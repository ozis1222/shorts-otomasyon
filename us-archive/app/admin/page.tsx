import Link from 'next/link';
import { redirect } from 'next/navigation';
import { isAdmin } from '@/lib/auth';
import { Orders, type OrderRow } from '@/db/repo';
import { webEnv } from '@/lib/env';
import { isConfigured, isConnected } from '@/server/etsy';
import { SeedButtons, EtsySync } from '@/components/AdminActions';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const STATE_LABELS: Record<string, string> = {
  WAITING_UPLOAD: 'Waiting on upload',
  QUEUED: 'Queued',
  PROCESSING: 'Generating',
  READY: 'Ready',
  DELIVERED: 'Delivered',
  FAILED: 'Failed',
};

export default function AdminDashboard({ searchParams }: { searchParams: Record<string, string> }) {
  if (!isAdmin()) redirect('/admin/login');
  const orders = Orders.all();
  const counts = orders.reduce<Record<string, number>>((acc, o) => {
    acc[o.state] = (acc[o.state] || 0) + 1;
    return acc;
  }, {});

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">The Us Archive</p>
            <h1 className="mt-1 font-editorial text-4xl">Seller dashboard</h1>
          </div>
          <Link href="/" className="text-sm text-inksoft hover:text-ink">
            View site →
          </Link>
        </div>

        {searchParams.etsy === 'connected' && (
          <p className="mt-4 rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700">Etsy connected.</p>
        )}
        {searchParams.etsy_error && (
          <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">Etsy: {searchParams.etsy_error}</p>
        )}

        {/* Status tiles */}
        <div className="mt-8 grid grid-cols-3 gap-4 sm:grid-cols-6">
          {['WAITING_UPLOAD', 'QUEUED', 'PROCESSING', 'READY', 'DELIVERED', 'FAILED'].map((s) => (
            <div key={s} className="rounded-2xl border border-hair bg-white p-4 text-center">
              <div className="font-editorial text-2xl">{counts[s] || 0}</div>
              <div className="mt-1 text-[11px] uppercase tracking-wide text-inksoft">{STATE_LABELS[s]}</div>
            </div>
          ))}
        </div>

        {/* Integrations + tools */}
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-hair bg-white p-6">
            <h2 className="font-semibold">Etsy integration</h2>
            <p className="mt-1 text-sm text-inksoft">
              {isConfigured()
                ? isConnected()
                  ? 'Connected. Sync to pull new paid orders.'
                  : 'Configured. Connect to authorize order access.'
                : 'Not configured — set ETSY_API_KEY / SECRET / SHOP_ID to enable.'}
            </p>
            {isConfigured() && (
              <div className="mt-4">
                <EtsySync connected={isConnected()} />
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-hair bg-white p-6">
            <h2 className="font-semibold">Test tools</h2>
            <p className="mt-1 text-sm text-inksoft">Create a mock order to exercise the full pipeline.</p>
            <div className="mt-4">
              <SeedButtons />
            </div>
            <p className="mt-3 text-xs text-inksoft">
              Order provider: <b>{webEnv.orderProvider}</b> · run <code>npm run worker</code> to process the queue.
            </p>
          </div>
        </div>

        {/* Orders table */}
        <h2 className="mt-12 font-editorial text-2xl">Orders</h2>
        <div className="mt-4 overflow-x-auto rounded-2xl border border-hair bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-hair text-xs uppercase tracking-wide text-inksoft">
              <tr>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3">Progress</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-inksoft">
                    No orders yet. Create a test order above.
                  </td>
                </tr>
              )}
              {orders.map((o: OrderRow) => (
                <tr key={o.id} className="border-b border-hair last:border-0 hover:bg-paper/50">
                  <td className="px-4 py-3">
                    <Link href={`/admin/order/${o.id}`} className="font-medium text-ink hover:text-ember">
                      {o.id}
                    </Link>
                    {o.buyer_name && <div className="text-xs text-inksoft">{o.buyer_name}</div>}
                  </td>
                  <td className="px-4 py-3 text-inksoft">{o.source}</td>
                  <td className="px-4 py-3">{o.package_id}</td>
                  <td className="px-4 py-3">
                    <StateBadge state={o.state} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-hair">
                      <div className="h-full bg-ember" style={{ width: `${o.progress}%` }} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-inksoft">{new Date(o.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

function StateBadge({ state }: { state: string }) {
  const color =
    state === 'DELIVERED'
      ? 'bg-green-100 text-green-800'
      : state === 'FAILED'
        ? 'bg-red-100 text-red-800'
        : state === 'PROCESSING'
          ? 'bg-amber-100 text-amber-800'
          : 'bg-gray-100 text-gray-700';
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${color}`}>{STATE_LABELS[state] || state}</span>;
}
