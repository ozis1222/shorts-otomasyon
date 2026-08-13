/** Order lifecycle: creation, secure links, retention purge. */
import { rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { getPackage } from '../src/config/packages.js';
import { generateSecureToken } from '../src/integrations/order-provider.js';
import { webEnv, ordersDir } from '../lib/env.js';
import { Orders, Uploads, Logs, type OrderRow } from '../db/repo.js';
import { getStorage, keys } from './storage.js';
import { sendEmail } from './email.js';

export interface CreateOrderInput {
  source: 'mock' | 'etsy';
  externalId?: string | null;
  packageId: string;
  buyerEmail?: string | null;
  buyerName?: string | null;
  theme?: 'light' | 'dark';
}

export function uploadLink(token: string): string {
  return `${webEnv.baseUrl}/onboarding/${token}`;
}
export function orderLink(token: string): string {
  return `${webEnv.baseUrl}/order/${token}`;
}

export async function createOrder(input: CreateOrderInput): Promise<OrderRow> {
  getPackage(input.packageId); // validate tier
  const id = `${input.source.toUpperCase()}-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
  const token = generateSecureToken();
  const now = new Date();
  const expires = new Date(now.getTime() + 30 * 86400000);
  Orders.insert({
    id,
    secure_token: token,
    source: input.source,
    external_id: input.externalId ?? null,
    package_id: input.packageId,
    buyer_email: input.buyerEmail ?? null,
    buyer_name: input.buyerName ?? null,
    state: 'WAITING_UPLOAD',
    stage: 'CREATED',
    progress: 0,
    error: null,
    theme: input.theme ?? 'light',
    uploaded_at: null,
    delivered_at: null,
    expires_at: expires.toISOString(),
    raw_deleted_at: null,
  });
  Logs.audit(id, 'order_created', `${input.source} ${input.packageId}`);
  const order = Orders.byId(id)!;
  if (order.buyer_email) {
    await sendEmail({ orderId: id, to: order.buyer_email, template: 'upload_your_memories', vars: { link: uploadLink(token) } });
  }
  return order;
}

/** Permanently delete a customer's raw chat (upload + on-disk file). */
export async function deleteRawData(orderId: string): Promise<void> {
  const storage = getStorage();
  await storage.remove(keys.chat(orderId)).catch(() => {});
  const workRaw = join(ordersDir(), orderId, 'raw-chat.txt');
  if (existsSync(workRaw)) await rm(workRaw).catch(() => {});
  const statsFile = join(ordersDir(), orderId, 'statistics.json');
  if (existsSync(statsFile)) await rm(statsFile).catch(() => {});
  Uploads.deleteChats(orderId);
  Orders.update(orderId, { raw_deleted_at: new Date().toISOString() });
  Logs.audit(orderId, 'raw_data_deleted');
}

/** Purge raw data for every delivered order past its retention window. */
export async function purgeExpiredRawData(): Promise<number> {
  let purged = 0;
  for (const o of Orders.all()) {
    if (o.raw_deleted_at || !o.delivered_at) continue;
    const ageDays = (Date.now() - new Date(o.delivered_at).getTime()) / 86400000;
    if (ageDays >= webEnv.retentionDays) {
      await deleteRawData(o.id);
      purged++;
    }
  }
  return purged;
}
