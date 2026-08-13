/** Typed data access. Thin, explicit queries — no ORM. */
import { getDb, nowIso } from './index.js';

export type OrderState =
  | 'WAITING_UPLOAD'
  | 'QUEUED'
  | 'PROCESSING'
  | 'READY'
  | 'DELIVERED'
  | 'FAILED';

export interface OrderRow {
  id: string;
  secure_token: string;
  source: string;
  external_id: string | null;
  package_id: string;
  buyer_email: string | null;
  buyer_name: string | null;
  state: OrderState;
  stage: string;
  progress: number;
  error: string | null;
  theme: string;
  created_at: string;
  updated_at: string;
  uploaded_at: string | null;
  delivered_at: string | null;
  expires_at: string | null;
  raw_deleted_at: string | null;
}

export const Orders = {
  insert(o: Omit<OrderRow, 'created_at' | 'updated_at'> & Partial<Pick<OrderRow, 'created_at' | 'updated_at'>>) {
    const now = nowIso();
    getDb()
      .prepare(
        `INSERT INTO orders (id, secure_token, source, external_id, package_id, buyer_email, buyer_name,
          state, stage, progress, error, theme, created_at, updated_at, uploaded_at, delivered_at, expires_at, raw_deleted_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      )
      .run(
        o.id, o.secure_token, o.source, o.external_id, o.package_id, o.buyer_email, o.buyer_name,
        o.state, o.stage, o.progress, o.error, o.theme, o.created_at ?? now, o.updated_at ?? now,
        o.uploaded_at, o.delivered_at, o.expires_at, o.raw_deleted_at,
      );
  },
  byId(id: string): OrderRow | undefined {
    return getDb().prepare('SELECT * FROM orders WHERE id = ?').get(id) as unknown as OrderRow | undefined;
  },
  byToken(token: string): OrderRow | undefined {
    return getDb().prepare('SELECT * FROM orders WHERE secure_token = ?').get(token) as unknown as OrderRow | undefined;
  },
  byExternalId(externalId: string): OrderRow | undefined {
    return getDb().prepare('SELECT * FROM orders WHERE external_id = ?').get(externalId) as unknown as OrderRow | undefined;
  },
  all(): OrderRow[] {
    return getDb().prepare('SELECT * FROM orders ORDER BY created_at DESC').all() as unknown as OrderRow[];
  },
  update(id: string, patch: Partial<OrderRow>) {
    const keys = Object.keys(patch);
    if (!keys.length) return;
    const set = keys.map((k) => `${k} = ?`).join(', ');
    const vals = keys.map((k) => (patch as any)[k]);
    getDb().prepare(`UPDATE orders SET ${set}, updated_at = ? WHERE id = ?`).run(...vals, nowIso(), id);
  },
};

export const Onboarding = {
  upsert(row: {
    order_id: string;
    partner_a: string;
    partner_b: string;
    language: string;
    tone: string;
    relationship_start: string | null;
    anniversary: string | null;
    first_date: string | null;
    first_trip: string | null;
    wedding_date: string | null;
    current_city: string | null;
    allow_humor: number;
    consent: number;
  }) {
    getDb()
      .prepare(
        `INSERT INTO onboarding (order_id, partner_a, partner_b, language, tone, relationship_start,
          anniversary, first_date, first_trip, wedding_date, current_city, allow_humor, consent, created_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
         ON CONFLICT(order_id) DO UPDATE SET partner_a=excluded.partner_a, partner_b=excluded.partner_b,
          language=excluded.language, tone=excluded.tone, relationship_start=excluded.relationship_start,
          anniversary=excluded.anniversary, first_date=excluded.first_date, first_trip=excluded.first_trip,
          wedding_date=excluded.wedding_date, current_city=excluded.current_city, allow_humor=excluded.allow_humor,
          consent=excluded.consent`,
      )
      .run(
        row.order_id, row.partner_a, row.partner_b, row.language, row.tone, row.relationship_start,
        row.anniversary, row.first_date, row.first_trip, row.wedding_date, row.current_city,
        row.allow_humor, row.consent, nowIso(),
      );
  },
  byOrder(orderId: string): any {
    return getDb().prepare('SELECT * FROM onboarding WHERE order_id = ?').get(orderId);
  },
};

export const Uploads = {
  insert(orderId: string, kind: string, filename: string, storageKey: string, bytes: number) {
    getDb()
      .prepare('INSERT INTO uploads (order_id, kind, filename, storage_key, bytes, created_at) VALUES (?,?,?,?,?,?)')
      .run(orderId, kind, filename, storageKey, bytes, nowIso());
  },
  byOrder(orderId: string): any[] {
    return getDb().prepare('SELECT * FROM uploads WHERE order_id = ? ORDER BY id').all(orderId);
  },
  deleteChats(orderId: string) {
    getDb().prepare("DELETE FROM uploads WHERE order_id = ? AND kind = 'chat'").run(orderId);
  },
};

export const Profiles = {
  upsert(orderId: string, statisticsJson: string, profileJson: string) {
    getDb()
      .prepare(
        `INSERT INTO profiles (order_id, statistics_json, profile_json, created_at) VALUES (?,?,?,?)
         ON CONFLICT(order_id) DO UPDATE SET statistics_json=excluded.statistics_json, profile_json=excluded.profile_json`,
      )
      .run(orderId, statisticsJson, profileJson, nowIso());
  },
  byOrder(orderId: string): { statistics_json: string; profile_json: string } | undefined {
    return getDb().prepare('SELECT statistics_json, profile_json FROM profiles WHERE order_id = ?').get(orderId) as any;
  },
};

export const Assets = {
  replaceForOrder(orderId: string, rows: { kind: string; filename: string; storageKey: string; bytes: number }[]) {
    const db = getDb();
    db.prepare('DELETE FROM assets WHERE order_id = ?').run(orderId);
    const stmt = db.prepare('INSERT INTO assets (order_id, kind, filename, storage_key, bytes, created_at) VALUES (?,?,?,?,?,?)');
    const now = nowIso();
    for (const r of rows) stmt.run(orderId, r.kind, r.filename, r.storageKey, r.bytes, now);
  },
  byOrder(orderId: string): any[] {
    return getDb().prepare('SELECT * FROM assets WHERE order_id = ? ORDER BY kind, filename').all(orderId);
  },
  byOrderAndFile(orderId: string, filename: string): any {
    return getDb().prepare('SELECT * FROM assets WHERE order_id = ? AND filename = ?').get(orderId, filename);
  },
};

export const Jobs = {
  enqueue(orderId: string) {
    getDb()
      .prepare("INSERT INTO jobs (order_id, status, attempts, created_at, updated_at) VALUES (?, 'queued', 0, ?, ?)")
      .run(orderId, nowIso(), nowIso());
  },
  claimNext(): { id: number; order_id: string; attempts: number } | undefined {
    const db = getDb();
    const job = db.prepare("SELECT * FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1").get() as any;
    if (!job) return undefined;
    db.prepare("UPDATE jobs SET status = 'running', attempts = attempts + 1, updated_at = ? WHERE id = ?").run(nowIso(), job.id);
    return job;
  },
  finish(id: number, status: 'done' | 'failed', error?: string) {
    getDb().prepare("UPDATE jobs SET status = ?, last_error = ?, updated_at = ? WHERE id = ?").run(status, error ?? null, nowIso(), id);
  },
  requeue(orderId: string) {
    getDb().prepare("UPDATE jobs SET status = 'queued', updated_at = ? WHERE order_id = ? AND status = 'failed'").run(nowIso(), orderId);
  },
};

export const Logs = {
  email(orderId: string | null, to: string, template: string) {
    getDb().prepare('INSERT INTO email_logs (order_id, to_addr, template, created_at) VALUES (?,?,?,?)').run(orderId, to, template, nowIso());
  },
  audit(orderId: string | null, event: string, detail?: string) {
    getDb().prepare('INSERT INTO audit_logs (order_id, event, detail, created_at) VALUES (?,?,?,?)').run(orderId, event, detail ?? null, nowIso());
  },
};

export const Integrations = {
  get(name: string): any | undefined {
    const row = getDb().prepare('SELECT data_json FROM integrations WHERE name = ?').get(name) as any;
    return row ? JSON.parse(row.data_json) : undefined;
  },
  set(name: string, data: unknown) {
    getDb()
      .prepare(
        `INSERT INTO integrations (name, data_json, updated_at) VALUES (?,?,?)
         ON CONFLICT(name) DO UPDATE SET data_json=excluded.data_json, updated_at=excluded.updated_at`,
      )
      .run(name, JSON.stringify(data), nowIso());
  },
};
