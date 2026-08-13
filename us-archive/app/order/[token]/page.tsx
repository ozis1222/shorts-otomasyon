import { Orders } from '@/db/repo';
import OrderPortal from '@/components/OrderPortal';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export default function OrderPage({ params }: { params: { token: string } }) {
  const order = Orders.byToken(params.token);
  if (!order) {
    return (
      <main className="min-h-screen bg-paper text-ink">
        <div className="mx-auto max-w-2xl px-6 py-16">
          <h1 className="font-editorial text-3xl">Order not found</h1>
          <p className="mt-3 text-inksoft">This link is invalid or has expired.</p>
        </div>
      </main>
    );
  }
  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">The Us Archive</p>
        <h1 className="mt-3 font-editorial text-4xl">
          {order.buyer_name ? order.buyer_name : 'Your archive'}
        </h1>
        <p className="mt-2 text-sm text-inksoft">Order {order.id}</p>
        <div className="mt-10">
          <OrderPortal token={order.secure_token} />
        </div>
      </div>
    </main>
  );
}
