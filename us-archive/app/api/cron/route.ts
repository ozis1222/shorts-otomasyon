import { NextResponse } from 'next/server';
import { webEnv } from '@/lib/env';
import { drainQueue } from '@/server/queue';
import { purgeExpiredRawData } from '@/server/orders';
import { syncOrders } from '@/server/etsy';
import { isConnected } from '@/server/etsy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 300;

/**
 * Scheduled worker tick for serverless deploys (call from Vercel Cron / GitHub
 * Actions every minute). Secured by ?key=APP_SECRET. For always-on hosts, run
 * `npm run worker` instead.
 */
async function handle(req: Request) {
  const key = new URL(req.url).searchParams.get('key');
  if (key !== webEnv.appSecret) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  let synced = { created: 0, scanned: 0 };
  if (webEnv.orderProvider === 'etsy' && isConnected()) {
    synced = await syncOrders().catch(() => ({ created: 0, scanned: 0 }));
  }
  const processed = await drainQueue(3);
  const purged = await purgeExpiredRawData();
  return NextResponse.json({ ok: true, synced, processed, purged });
}

export const GET = handle;
export const POST = handle;
