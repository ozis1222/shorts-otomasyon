'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function SeedButtons() {
  const router = useRouter();
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function seed(mode: 'link' | 'demo') {
    setBusy(true);
    setMsg(null);
    const res = await fetch('/api/dev/seed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, packageId: 'full' }),
    });
    const data = await res.json();
    setBusy(false);
    if (!res.ok) return setMsg(data.error || 'Failed');
    setMsg(mode === 'demo' ? `Demo order queued: ${data.orderId}` : `Upload link: ${data.uploadUrl}`);
    router.refresh();
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button onClick={() => seed('demo')} disabled={busy} className="rounded-full bg-ember px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
        + Test order (auto-run Alex &amp; Mia)
      </button>
      <button onClick={() => seed('link')} disabled={busy} className="rounded-full border border-hair px-5 py-2 text-sm font-semibold hover:border-ink disabled:opacity-50">
        + Empty order (get upload link)
      </button>
      {msg && <span className="text-sm text-inksoft">{msg}</span>}
    </div>
  );
}

export function EtsySync({ connected }: { connected: boolean }) {
  const router = useRouter();
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!connected) {
    return (
      <a href="/api/etsy/connect" className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-white hover:opacity-90">
        Connect Etsy
      </a>
    );
  }
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={async () => {
          setBusy(true);
          setMsg(null);
          const res = await fetch('/api/etsy/sync', { method: 'POST' });
          const data = await res.json();
          setBusy(false);
          setMsg(res.ok ? `Synced: ${data.created} new / ${data.scanned} scanned` : data.error);
          router.refresh();
        }}
        disabled={busy}
        className="rounded-full border border-hair px-5 py-2 text-sm font-semibold hover:border-ink disabled:opacity-50"
      >
        {busy ? 'Syncing…' : 'Sync Etsy orders'}
      </button>
      {msg && <span className="text-sm text-inksoft">{msg}</span>}
    </div>
  );
}

export function RetryButton({ orderId }: { orderId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      onClick={async () => {
        setBusy(true);
        await fetch('/api/admin/retry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ orderId }),
        });
        setBusy(false);
        router.refresh();
      }}
      disabled={busy}
      className="rounded-full bg-ember px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
    >
      {busy ? 'Retrying…' : 'Retry'}
    </button>
  );
}
