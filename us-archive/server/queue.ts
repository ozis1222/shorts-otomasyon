/**
 * DB-backed job queue (spec §33 — keeps the MVP simple, no Redis). PDF/AI work
 * runs here, never inside an HTTP request. Failures are recorded and retryable.
 */
import { Jobs, Orders } from '../db/repo.js';
import { processOrder } from './process-order.js';
import { closeBrowser } from '../src/render/browser.js';

/** Claim and process a single queued job. Returns true if one was handled. */
export async function runOneJob(): Promise<boolean> {
  const job = Jobs.claimNext();
  if (!job) return false;
  const order = Orders.byId(job.order_id);
  if (!order) {
    Jobs.finish(job.id, 'failed', 'order not found');
    return true;
  }
  try {
    await processOrder(order);
    Jobs.finish(job.id, 'done');
  } catch (err) {
    const msg = String(err instanceof Error ? err.stack || err.message : err);
    Jobs.finish(job.id, 'failed', msg.slice(0, 1000));
    Orders.update(order.id, { state: 'FAILED', error: msg.slice(0, 500) });
  }
  return true;
}

/** Drain all currently-queued jobs (used by the cron endpoint). */
export async function drainQueue(max = 5): Promise<number> {
  let n = 0;
  while (n < max && (await runOneJob())) n++;
  await closeBrowser();
  return n;
}
