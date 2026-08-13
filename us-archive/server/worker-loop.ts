/** Standalone worker loop for local dev: `npm run worker`. */
import { runOneJob } from './queue.js';
import { purgeExpiredRawData } from './orders.js';

const POLL_MS = 3000;
let lastPurge = 0;

async function tick() {
  try {
    const handled = await runOneJob();
    // Run retention purge at most hourly.
    if (Date.now() - lastPurge > 3600_000) {
      lastPurge = Date.now();
      const n = await purgeExpiredRawData();
      if (n) console.log(`[worker] purged raw data for ${n} order(s)`);
    }
    if (handled) return tick(); // keep draining while there's work
  } catch (err) {
    console.error('[worker] error', err);
  }
  setTimeout(tick, POLL_MS);
}

console.log('[worker] started — polling for jobs every', POLL_MS, 'ms');
tick();
