import { NextResponse } from 'next/server';
import { isAdmin } from '@/lib/auth';
import { Orders, Jobs, Logs } from '@/db/repo';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  if (!isAdmin()) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orderId } = await req.json();
  const order = Orders.byId(orderId);
  if (!order) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  Orders.update(order.id, { state: 'QUEUED', error: null, stage: 'UPLOADED', progress: 5 });
  Jobs.requeue(order.id);
  Jobs.enqueue(order.id);
  Logs.audit(order.id, 'retry_requested');
  return NextResponse.json({ ok: true });
}
