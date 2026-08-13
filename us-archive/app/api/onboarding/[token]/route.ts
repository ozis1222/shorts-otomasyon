import { NextResponse } from 'next/server';
import { Orders, Onboarding, Uploads, Logs } from '@/db/repo';
import { getStorage, keys } from '@/server/storage';
import { orderLink } from '@/server/orders';
import { sendEmail } from '@/server/email';
import { Jobs } from '@/db/repo';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_CHAT_BYTES = 40 * 1024 * 1024;

export async function POST(req: Request, { params }: { params: { token: string } }) {
  const order = Orders.byToken(params.token);
  if (!order) return NextResponse.json({ error: 'Order not found' }, { status: 404 });
  if (order.state !== 'WAITING_UPLOAD' && order.state !== 'FAILED') {
    return NextResponse.json({ error: 'This order has already been submitted.' }, { status: 409 });
  }

  const form = await req.formData();
  const consent = form.get('consent') === 'true' || form.get('consent') === 'on';
  if (!consent) return NextResponse.json({ error: 'Consent is required to process your chat.' }, { status: 400 });

  const partnerA = String(form.get('partnerA') || '').trim();
  const partnerB = String(form.get('partnerB') || '').trim();
  if (!partnerA || !partnerB) return NextResponse.json({ error: 'Both partner names are required.' }, { status: 400 });

  const chat = form.get('chat');
  if (!(chat instanceof File) || chat.size === 0) {
    return NextResponse.json({ error: 'Please upload your WhatsApp .txt export.' }, { status: 400 });
  }
  if (chat.size > MAX_CHAT_BYTES) {
    return NextResponse.json({ error: 'Chat file is too large (40MB max).' }, { status: 413 });
  }

  const storage = getStorage();
  const buf = Buffer.from(await chat.arrayBuffer());
  await storage.put(keys.chat(order.id), buf);
  Uploads.insert(order.id, 'chat', chat.name || 'chat.txt', keys.chat(order.id), buf.length);

  // Optional photos (0–20).
  const photos = form.getAll('photos').filter((p): p is File => p instanceof File && p.size > 0).slice(0, 20);
  let n = 0;
  for (const photo of photos) {
    n++;
    const pbuf = Buffer.from(await photo.arrayBuffer());
    await storage.put(keys.photo(order.id, n), pbuf);
    Uploads.insert(order.id, 'photo', photo.name || `photo-${n}.jpg`, keys.photo(order.id, n), pbuf.length);
  }

  Onboarding.upsert({
    order_id: order.id,
    partner_a: partnerA,
    partner_b: partnerB,
    language: String(form.get('language') || 'en'),
    tone: String(form.get('tone') || 'balanced'),
    relationship_start: str(form.get('relationshipStart')),
    anniversary: str(form.get('anniversary')),
    first_date: str(form.get('firstDate')),
    first_trip: str(form.get('firstTrip')),
    wedding_date: str(form.get('weddingDate')),
    current_city: str(form.get('currentCity')),
    allow_humor: form.get('allowHumor') === 'true' || form.get('allowHumor') === 'on' ? 1 : 0,
    consent: 1,
  });

  Orders.update(order.id, { state: 'QUEUED', stage: 'UPLOADED', progress: 5, uploaded_at: new Date().toISOString(), buyer_name: partnerA });
  Jobs.enqueue(order.id);
  Logs.audit(order.id, 'uploaded', `photos=${n}`);

  if (order.buyer_email) {
    await sendEmail({ orderId: order.id, to: order.buyer_email, template: 'archive_in_progress', vars: { link: orderLink(order.secure_token) } });
  }

  return NextResponse.json({ ok: true, orderUrl: `/order/${order.secure_token}` });
}

function str(v: FormDataEntryValue | null): string | null {
  const s = v == null ? '' : String(v).trim();
  return s || null;
}
