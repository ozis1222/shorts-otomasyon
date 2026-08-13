import { NextResponse } from 'next/server';
import { Orders } from '@/db/repo';
import { deleteRawData } from '@/server/orders';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(_req: Request, { params }: { params: { token: string } }) {
  const order = Orders.byToken(params.token);
  if (!order) return NextResponse.json({ error: 'Order not found' }, { status: 404 });
  await deleteRawData(order.id);
  return NextResponse.json({ ok: true });
}
