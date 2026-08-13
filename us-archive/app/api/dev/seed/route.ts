import { NextResponse } from 'next/server';
import { isAdmin } from '@/lib/auth';
import { createOrder, uploadLink, orderLink } from '@/server/orders';
import { Orders, Onboarding, Uploads, Jobs, Logs } from '@/db/repo';
import { getStorage, keys } from '@/server/storage';
import { generateSyntheticChat } from '@/src/synthetic/generator';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/**
 * Dev helper (admin only): create a mock order.
 *   { mode: "link" }  -> empty order, returns the customer upload link
 *   { mode: "demo" }  -> auto-fills Alex & Mia + a synthetic chat and queues it
 */
export async function POST(req: Request) {
  if (!isAdmin()) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const packageId = body.packageId || 'full';
  const mode = body.mode || 'link';
  const order = await createOrder({ source: 'mock', packageId, buyerEmail: body.email || null, theme: body.theme || 'light' });

  if (mode === 'demo') {
    const raw = generateSyntheticChat({ partnerA: 'Alex', partnerB: 'Mia', months: 36, targetMessages: 20000, seed: 42 });
    await getStorage().put(keys.chat(order.id), Buffer.from(raw));
    Uploads.insert(order.id, 'chat', 'alex-mia.txt', keys.chat(order.id), raw.length);
    Onboarding.upsert({
      order_id: order.id,
      partner_a: 'Alex',
      partner_b: 'Mia',
      language: 'en',
      tone: 'balanced',
      relationship_start: '2022-06-15',
      anniversary: '2023-06-15',
      first_date: '2022-06-20',
      first_trip: '2022-09-10',
      wedding_date: null,
      current_city: 'Istanbul',
      allow_humor: 1,
      consent: 1,
    });
    Orders.update(order.id, { state: 'QUEUED', stage: 'UPLOADED', progress: 5, uploaded_at: new Date().toISOString(), buyer_name: 'Alex & Mia' });
    Jobs.enqueue(order.id);
    Logs.audit(order.id, 'dev_demo_seeded');
    return NextResponse.json({ ok: true, orderId: order.id, orderUrl: orderLink(order.secure_token) });
  }

  return NextResponse.json({ ok: true, orderId: order.id, uploadUrl: uploadLink(order.secure_token) });
}
