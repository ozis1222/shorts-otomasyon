import Link from 'next/link';
import { redirect } from 'next/navigation';
import { isAdmin } from '@/lib/auth';
import { Orders, Assets, Onboarding } from '@/db/repo';
import { orderLink, uploadLink } from '@/server/orders';
import { RetryButton } from '@/components/AdminActions';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const STAGES = ['UPLOADED', 'PARSED', 'STATISTICS_READY', 'AI_ANALYZED', 'PROFILE_READY', 'PDF_READY', 'ASSETS_READY', 'DELIVERED'];

export default function OrderDetail({ params }: { params: { id: string } }) {
  if (!isAdmin()) redirect('/admin/login');
  const order = Orders.byId(params.id);
  if (!order) {
    return (
      <Shell>
        <p>Order not found.</p>
      </Shell>
    );
  }
  const ob = Onboarding.byOrder(order.id);
  const assets = Assets.byOrder(order.id);
  const currentIdx = STAGES.indexOf(order.stage);

  return (
    <Shell>
      <Link href="/admin" className="text-sm text-inksoft hover:text-ink">
        ← All orders
      </Link>
      <h1 className="mt-3 font-editorial text-3xl">{order.id}</h1>
      <p className="mt-1 text-sm text-inksoft">
        {order.source} · {order.package_id} · {order.buyer_email || 'no email'} · created {new Date(order.created_at).toLocaleString()}
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        {(order.state === 'FAILED' || order.state === 'DELIVERED') && <RetryButton orderId={order.id} />}
        {order.state === 'WAITING_UPLOAD' && (
          <a href={uploadLink(order.secure_token)} className="rounded-full border border-hair px-5 py-2 text-sm font-semibold hover:border-ink">
            Customer upload link
          </a>
        )}
        <a href={orderLink(order.secure_token)} className="rounded-full border border-hair px-5 py-2 text-sm font-semibold hover:border-ink">
          Customer portal
        </a>
      </div>

      {order.error && <p className="mt-6 whitespace-pre-wrap rounded-xl bg-red-50 p-4 text-sm text-red-700">{order.error}</p>}

      {/* Pipeline */}
      <h2 className="mt-10 font-editorial text-xl">Pipeline</h2>
      <ul className="mt-4 space-y-2">
        {STAGES.map((s, i) => {
          const done = order.state === 'DELIVERED' || i < currentIdx;
          const active = i === currentIdx && order.state !== 'DELIVERED';
          const failed = order.state === 'FAILED' && i === currentIdx;
          return (
            <li key={s} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                  failed ? 'bg-red-500 text-white' : done ? 'bg-ember text-white' : active ? 'border-2 border-ember' : 'border border-hair'
                }`}
              >
                {failed ? '×' : done ? '✓' : active ? '→' : '○'}
              </span>
              <span className={done || active ? 'text-ink' : 'text-inksoft'}>{s}</span>
            </li>
          );
        })}
      </ul>

      {/* Onboarding */}
      {ob && (
        <>
          <h2 className="mt-10 font-editorial text-xl">Onboarding</h2>
          <div className="mt-3 rounded-2xl border border-hair bg-white p-5 text-sm">
            <p>
              <b>{ob.partner_a}</b> &amp; <b>{ob.partner_b}</b> · tone {ob.tone} · {ob.language}
            </p>
            <p className="mt-1 text-inksoft">
              Consent: {ob.consent ? 'yes' : 'no'} · Humor allowed: {ob.allow_humor ? 'yes' : 'no'}
            </p>
          </div>
        </>
      )}

      {/* Assets */}
      {assets.length > 0 && (
        <>
          <h2 className="mt-10 font-editorial text-xl">Delivered assets ({assets.length})</h2>
          <ul className="mt-3 divide-y divide-hair rounded-2xl border border-hair bg-white text-sm">
            {assets.map((a: any) => (
              <li key={a.filename} className="flex items-center justify-between px-5 py-2.5">
                <span>
                  <span className="text-inksoft">[{a.kind}]</span> {a.filename}
                </span>
                <a href={`/api/download/${order.secure_token}/${a.filename}`} className="text-ember hover:underline">
                  {(a.bytes / 1024).toFixed(0)} KB
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-3xl px-6 py-12">{children}</div>
    </main>
  );
}
