/**
 * Order processor: takes a queued order, runs it through the engine pipeline,
 * persists the profile + assets, and marks it delivered. Progress and per-stage
 * state are written to the DB so the admin and customer UIs can show live
 * status. Idempotent — safe to re-run after a failure (spec §34).
 */
import { readdir, stat } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { webEnv } from '../lib/env.js';
import { CoupleSchema } from '../src/profile/schema.js';
import { runPipeline, type Stage } from '../src/pipeline/orchestrator.js';
import { Orders, Onboarding, Profiles, Assets, Logs, type OrderRow } from '../db/repo.js';
import { getStorage, keys } from './storage.js';
import { orderLink } from './orders.js';
import { sendEmail } from './email.js';

const STAGE_PROGRESS: Record<Stage, number> = {
  UPLOADED: 5,
  PARSED: 15,
  STATISTICS_READY: 30,
  AI_ANALYZED: 55,
  PROFILE_READY: 60,
  PDF_READY: 80,
  ASSETS_READY: 95,
  DELIVERED: 100,
};

function storageWorkDir(orderId: string): string {
  return join(webEnv.dataDir, 'storage', 'orders', orderId);
}

function assetKind(rel: string): string {
  if (rel === 'archive.pdf') return 'pdf';
  if (rel.startsWith('stories/')) return 'story';
  if (rel.startsWith('instagram/')) return 'instagram';
  if (rel.startsWith('wallpapers/')) return 'wallpaper';
  if (rel.includes('fingerprint-poster')) return 'poster';
  if (rel.includes('fingerprint')) return 'fingerprint';
  if (rel.endsWith('.json')) return 'profile';
  return 'other';
}

async function walk(dir: string, base: string): Promise<string[]> {
  const out: string[] = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await walk(full, base)));
    else out.push(relative(base, full));
  }
  return out;
}

export async function processOrder(order: OrderRow): Promise<void> {
  const storage = getStorage();
  const ob = Onboarding.byOrder(order.id);
  if (!ob) throw new Error('Onboarding not completed');

  const rawChat = (await storage.get(keys.chat(order.id))).toString('utf8');
  const couple = CoupleSchema.parse({
    partnerA: ob.partner_a,
    partnerB: ob.partner_b,
    language: ob.language,
    tone: ob.tone,
    relationshipStartDate: ob.relationship_start,
    anniversaryDate: ob.anniversary,
    firstDate: ob.first_date,
    firstTrip: ob.first_trip,
    weddingDate: ob.wedding_date,
    currentCity: ob.current_city,
  });

  Orders.update(order.id, { state: 'PROCESSING', error: null, progress: 5, stage: 'UPLOADED' });

  const workDir = storageWorkDir(order.id);
  const result = await runPipeline(
    {
      orderId: order.id,
      workDir,
      rawChat,
      couple,
      packageId: order.package_id,
      theme: order.theme as 'light' | 'dark',
      force: true,
    },
    (event, data) => {
      if (event === 'stage' && data?.stage) {
        const stage = data.stage as Stage;
        Orders.update(order.id, { stage, progress: STAGE_PROGRESS[stage] ?? order.progress });
      }
      Logs.audit(order.id, `pipeline_${event}`, data ? JSON.stringify(data).slice(0, 500) : undefined);
    },
  );

  // Persist compact data (spec §31: no raw messages in the DB).
  Profiles.upsert(order.id, JSON.stringify(result.statistics), JSON.stringify(result.profile));

  // Register delivered assets (archive dir + zip).
  const archiveDir = join(workDir, 'archive');
  const files = await walk(archiveDir, archiveDir);
  const rows: { kind: string; filename: string; storageKey: string; bytes: number }[] = [];
  for (const rel of files) {
    const s = await stat(join(archiveDir, rel));
    rows.push({ kind: assetKind(rel), filename: rel, storageKey: keys.asset(order.id, rel), bytes: s.size });
  }
  const zipStat = await stat(result.zipPath);
  rows.push({ kind: 'zip', filename: `the-us-archive-${order.id}.zip`, storageKey: keys.zip(order.id), bytes: zipStat.size });
  Assets.replaceForOrder(order.id, rows);

  Orders.update(order.id, {
    state: 'DELIVERED',
    stage: 'DELIVERED',
    progress: 100,
    delivered_at: new Date().toISOString(),
    uploaded_at: order.uploaded_at ?? new Date().toISOString(),
  });
  Logs.audit(order.id, 'delivered', `${rows.length} assets`);

  if (order.buyer_email) {
    await sendEmail({ orderId: order.id, to: order.buyer_email, template: 'archive_ready', vars: { link: orderLink(order.secure_token) } });
  }
}
