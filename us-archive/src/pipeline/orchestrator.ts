/**
 * End-to-end order pipeline with explicit, resumable stages (spec §34). Each
 * stage persists its output under the order's working directory; re-running the
 * pipeline skips stages whose artifact already exists unless `force` is set, so
 * a crash mid-way never forces a full restart. Raw chat is deleted after the
 * retention window (spec §4).
 */
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { config } from '../config/index.js';
import type { Couple } from '../profile/schema.js';
import { RelationshipProfileSchema, type RelationshipProfile } from '../profile/schema.js';
import { parseWhatsApp } from '../parser/whatsapp.js';
import { computeStatistics, type Statistics } from '../stats/statistics.js';
import { analyze } from './analyze.js';
import { createProvider } from '../ai/provider.js';
import { renderPDF } from '../render/pdf.js';
import { renderSocialAssets } from '../render/social.js';
import { zipDirectory } from '../packaging/zip.js';
import { closeBrowser } from '../render/browser.js';

export type Stage =
  | 'UPLOADED'
  | 'PARSED'
  | 'STATISTICS_READY'
  | 'AI_ANALYZED'
  | 'PROFILE_READY'
  | 'PDF_READY'
  | 'ASSETS_READY'
  | 'DELIVERED';

export interface PipelineInput {
  orderId: string;
  workDir: string;
  rawChat: string;
  couple: Couple;
  packageId: string;
  theme?: 'light' | 'dark';
  force?: boolean;
}

export interface PipelineResult {
  orderId: string;
  profile: RelationshipProfile;
  statistics: Statistics;
  pdfPath: string;
  zipPath: string;
  assetCount: number;
  parserMeta: ReturnType<typeof parseWhatsApp>['meta'];
}

type Logger = (event: string, data?: Record<string, unknown>) => void;

export async function runPipeline(input: PipelineInput, log: Logger = () => {}): Promise<PipelineResult> {
  const { orderId, workDir, couple, packageId } = input;
  const deliverDir = join(workDir, 'archive');
  await mkdir(deliverDir, { recursive: true });

  const stamp = (stage: Stage) => log('stage', { orderId, stage });
  const t0 = Date.now();

  // --- Stage PARSED ---------------------------------------------------------
  stamp('UPLOADED');
  const parsed = parseWhatsApp(input.rawChat);
  stamp('PARSED');
  log('parsed', { orderId, ...parsed.meta }); // meta only — never raw content

  if (parsed.participants.length < 2) {
    throw new Error(`Parser found ${parsed.participants.length} participant(s); need at least 2.`);
  }

  // --- Stage STATISTICS_READY ----------------------------------------------
  const statsPath = join(workDir, 'statistics.json');
  let statistics: Statistics;
  if (existsSync(statsPath) && !input.force) {
    statistics = JSON.parse(await readFile(statsPath, 'utf8'));
  } else {
    statistics = computeStatistics(parsed.messages);
    await writeFile(statsPath, JSON.stringify(statistics, null, 2));
  }
  stamp('STATISTICS_READY');

  // --- Stage AI_ANALYZED / PROFILE_READY -----------------------------------
  const profilePath = join(workDir, 'relationship-profile.json');
  let profile: RelationshipProfile;
  if (existsSync(profilePath) && !input.force) {
    profile = RelationshipProfileSchema.parse(JSON.parse(await readFile(profilePath, 'utf8')));
  } else {
    const provider = createProvider();
    log('ai.provider', { orderId, provider: provider.name });
    profile = await analyze(parsed.messages, statistics, couple, packageId, provider, (stage, extra) =>
      log('ai', { orderId, stage, ...extra }),
    );
    await writeFile(profilePath, JSON.stringify(profile, null, 2));
  }
  stamp('AI_ANALYZED');
  // Copy the canonical profile into the delivered archive too.
  await writeFile(join(deliverDir, 'relationship-profile.json'), JSON.stringify(profile, null, 2));
  stamp('PROFILE_READY');

  // --- Stage PDF_READY ------------------------------------------------------
  const pdfPath = join(deliverDir, 'archive.pdf');
  if (!existsSync(pdfPath) || input.force) {
    const { bytes } = await renderPDF(profile, pdfPath, { theme: input.theme });
    log('pdf', { orderId, bytes });
  }
  stamp('PDF_READY');

  // --- Stage ASSETS_READY ---------------------------------------------------
  const assets = await renderSocialAssets(profile, deliverDir, input.theme ?? 'light');
  log('assets', { orderId, count: assets.length });
  stamp('ASSETS_READY');
  await closeBrowser();

  // --- Stage DELIVERED ------------------------------------------------------
  const zipPath = join(workDir, `the-us-archive-${orderId}.zip`);
  const { bytes: zipBytes } = await zipDirectory(deliverDir, zipPath);
  log('delivered', { orderId, zipBytes, durationMs: Date.now() - t0 });
  stamp('DELIVERED');

  return {
    orderId,
    profile,
    statistics,
    pdfPath,
    zipPath,
    assetCount: assets.length,
    parserMeta: parsed.meta,
  };
}

/** Privacy: remove the raw chat + intermediate parse artifacts for an order. */
export async function deleteRawData(workDir: string): Promise<void> {
  for (const f of ['raw-chat.txt', 'statistics.json']) {
    const p = join(workDir, f);
    if (existsSync(p)) await rm(p);
  }
}

/** Whether an order's raw data is past its retention window and should be purged. */
export function isPastRetention(uploadedAt: Date, now = new Date()): boolean {
  const ageDays = (now.getTime() - uploadedAt.getTime()) / 86400000;
  return ageDays >= config.rawDataRetentionDays;
}
