import { redirect } from 'next/navigation';
import { Orders } from '@/db/repo';
import { getPackage } from '@/src/config/packages';
import OnboardingForm from '@/components/OnboardingForm';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export default function OnboardingPage({ params }: { params: { token: string } }) {
  const order = Orders.byToken(params.token);
  if (!order) {
    return (
      <Shell>
        <h1 className="font-editorial text-3xl">Link not found</h1>
        <p className="mt-3 text-inksoft">This upload link is invalid or has expired. Check your order confirmation email.</p>
      </Shell>
    );
  }
  if (order.state !== 'WAITING_UPLOAD' && order.state !== 'FAILED') {
    redirect(`/order/${order.secure_token}`);
  }
  const pkg = getPackage(order.package_id);

  return (
    <Shell>
      <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">The Us Archive · {pkg.name}</p>
      <h1 className="mt-3 font-editorial text-4xl">Let&apos;s build your archive</h1>
      <p className="mt-3 max-w-xl text-inksoft">
        A few details and your chat export — that&apos;s all we need. This takes about two minutes.
      </p>
      <div className="mt-10">
        <OnboardingForm token={order.secure_token} />
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-2xl px-6 py-16">{children}</div>
    </main>
  );
}
