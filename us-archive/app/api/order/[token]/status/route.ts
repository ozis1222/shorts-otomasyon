import { NextResponse } from 'next/server';
import { Orders, Assets } from '@/db/repo';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(_req: Request, { params }: { params: { token: string } }) {
  const order = Orders.byToken(params.token);
  if (!order) return NextResponse.json({ error: 'Order not found' }, { status: 404 });
  const assets = order.state === 'DELIVERED' ? Assets.byOrder(order.id) : [];
  return NextResponse.json({
    id: order.id,
    state: order.state,
    stage: order.stage,
    progress: order.progress,
    error: order.state === 'FAILED' ? 'Something went wrong while generating your archive. Our team has been notified.' : null,
    rawDeleted: Boolean(order.raw_deleted_at),
    packageId: order.package_id,
    assets: assets.map((a: any) => ({ kind: a.kind, filename: a.filename, bytes: a.bytes })),
  });
}
