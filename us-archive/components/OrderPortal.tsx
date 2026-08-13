'use client';
import { useEffect, useState } from 'react';

interface Asset {
  kind: string;
  filename: string;
  bytes: number;
}
interface Status {
  state: string;
  stage: string;
  progress: number;
  error: string | null;
  rawDeleted: boolean;
  packageId: string;
  assets: Asset[];
}

const STAGE_STEPS = [
  ['PARSED', 'Chat parsed'],
  ['STATISTICS_READY', 'Statistics computed'],
  ['AI_ANALYZED', 'AI analysis'],
  ['PROFILE_READY', 'Relationship profile'],
  ['PDF_READY', 'Magazine rendered'],
  ['ASSETS_READY', 'Social assets'],
  ['DELIVERED', 'Delivered'],
] as const;
const ORDER = STAGE_STEPS.map((s) => s[0]);

export default function OrderPortal({ token }: { token: string }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      const res = await fetch(`/api/order/${token}/status`, { cache: 'no-store' });
      if (!res.ok) return;
      const data: Status = await res.json();
      if (!active) return;
      setStatus(data);
      if (data.state !== 'DELIVERED' && data.state !== 'FAILED') setTimeout(poll, 2500);
    };
    poll();
    return () => {
      active = false;
    };
  }, [token]);

  if (!status) return <p className="text-inksoft">Loading…</p>;

  const dl = (f: string) => `/api/download/${token}/${f}`;
  const has = (kind: string) => status.assets.filter((a) => a.kind === kind);
  const stories = has('story').slice(0, 3);

  if (status.state === 'DELIVERED') {
    return (
      <div className="space-y-10">
        <div className="rounded-2xl border border-hair bg-white p-8 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">Ready</p>
          <h2 className="mt-2 font-editorial text-3xl">Your archive is ready 🎉</h2>
          <div className="mt-6 flex flex-wrap justify-center gap-4">
            <a href={dl(status.assets.find((a) => a.kind === 'zip')?.filename || '')} className="rounded-full bg-ember px-8 py-4 font-semibold text-white hover:opacity-90">
              Download everything (.zip)
            </a>
            <a href={dl('archive.pdf')} className="rounded-full border border-ink px-8 py-4 font-semibold hover:opacity-80">
              Open the magazine (PDF)
            </a>
          </div>
        </div>

        <div>
          <h3 className="mb-4 font-editorial text-2xl">Preview</h3>
          <div className="grid gap-6 sm:grid-cols-2">
            <img src={dl('relationship-fingerprint.png')} alt="Relationship fingerprint" className="w-full rounded-2xl border border-hair bg-white" />
            <div className="grid grid-cols-3 gap-3">
              {stories.map((s) => (
                <img key={s.filename} src={dl(s.filename)} alt="story card" className="w-full rounded-xl border border-hair" />
              ))}
            </div>
          </div>
        </div>

        <div>
          <h3 className="mb-4 font-editorial text-2xl">All files</h3>
          <ul className="divide-y divide-hair rounded-2xl border border-hair bg-white">
            {status.assets.map((a) => (
              <li key={a.filename} className="flex items-center justify-between px-5 py-3 text-sm">
                <span>{a.filename}</span>
                <a href={dl(a.filename)} className="text-ember hover:underline">
                  Download
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-hair bg-white p-6">
          <h3 className="font-semibold">Your privacy</h3>
          {status.rawDeleted ? (
            <p className="mt-2 text-sm text-inksoft">Your uploaded chat has been deleted. Your archive files remain available until your link expires.</p>
          ) : (
            <>
              <p className="mt-2 text-sm text-inksoft">
                Your raw chat is auto-deleted after the retention window. You can also delete it right now — your finished
                files stay available.
              </p>
              <button
                onClick={async () => {
                  if (!confirm('Permanently delete your uploaded chat now?')) return;
                  setDeleting(true);
                  await fetch(`/api/order/${token}/delete`, { method: 'POST' });
                  const res = await fetch(`/api/order/${token}/status`, { cache: 'no-store' });
                  setStatus(await res.json());
                  setDeleting(false);
                }}
                disabled={deleting}
                className="mt-4 rounded-full border border-red-300 px-6 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete my chat data'}
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  if (status.state === 'FAILED') {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8">
        <h2 className="font-editorial text-2xl text-red-800">We hit a snag</h2>
        <p className="mt-2 text-sm text-red-700">{status.error}</p>
        <p className="mt-2 text-sm text-red-700">Our team has been notified and will re-run your archive.</p>
      </div>
    );
  }

  // In progress
  const currentIdx = Math.max(0, ORDER.indexOf(status.stage as any));
  return (
    <div className="rounded-2xl border border-hair bg-white p-8">
      <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">Building your archive</p>
      <h2 className="mt-2 font-editorial text-3xl">Hang tight — this usually takes a few minutes.</h2>
      <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-hair">
        <div className="h-full bg-ember transition-all" style={{ width: `${status.progress}%` }} />
      </div>
      <ul className="mt-8 space-y-3">
        {STAGE_STEPS.map(([key, label], i) => {
          const done = i < currentIdx || status.stage === 'DELIVERED';
          const active = i === currentIdx;
          return (
            <li key={key} className="flex items-center gap-3 text-sm">
              <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${done ? 'bg-ember text-white' : active ? 'border-2 border-ember text-ember' : 'border border-hair text-inksoft'}`}>
                {done ? '✓' : active ? '…' : ''}
              </span>
              <span className={done || active ? 'text-ink' : 'text-inksoft'}>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
