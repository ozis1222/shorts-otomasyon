'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const TONES = ['romantic', 'funny', 'balanced', 'minimal', 'emotional'] as const;

export default function OnboardingForm({ token }: { token: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatName, setChatName] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const fd = new FormData(e.currentTarget);
      const res = await fetch(`/api/onboarding/${token}`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Something went wrong.');
      router.push(data.orderUrl);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
      setBusy(false);
    }
  }

  const field = 'w-full rounded-xl border border-hair bg-white px-4 py-3 text-ink outline-none focus:border-ember';
  const label = 'mb-1 block text-sm font-medium';

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className={label}>Partner 1 name *</label>
          <input name="partnerA" required className={field} placeholder="Alex" />
        </div>
        <div>
          <label className={label}>Partner 2 name *</label>
          <input name="partnerB" required className={field} placeholder="Mia" />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className={label}>Relationship start</label>
          <input type="date" name="relationshipStart" className={field} />
        </div>
        <div>
          <label className={label}>Anniversary (optional)</label>
          <input type="date" name="anniversary" className={field} />
        </div>
        <div>
          <label className={label}>First date (optional)</label>
          <input type="date" name="firstDate" className={field} />
        </div>
        <div>
          <label className={label}>First trip (optional)</label>
          <input type="date" name="firstTrip" className={field} />
        </div>
        <div>
          <label className={label}>Wedding (optional)</label>
          <input type="date" name="weddingDate" className={field} />
        </div>
        <div>
          <label className={label}>Current city (optional)</label>
          <input name="currentCity" className={field} placeholder="Istanbul" />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className={label}>Language</label>
          <select name="language" className={field} defaultValue="en">
            <option value="en">English</option>
            <option value="tr">Türkçe</option>
          </select>
        </div>
        <div>
          <label className={label}>Tone</label>
          <select name="tone" className={field} defaultValue="balanced">
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className={label}>Your WhatsApp chat (.txt) *</label>
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-hair bg-white px-6 py-10 text-center transition hover:border-ember">
          <span className="text-sm font-medium">{chatName ?? 'Click to choose your exported .txt file'}</span>
          <span className="mt-1 text-xs text-inksoft">Export → Without media works great. 40MB max.</span>
          <input
            type="file"
            name="chat"
            accept=".txt,text/plain"
            required
            className="hidden"
            onChange={(e) => setChatName(e.target.files?.[0]?.name ?? null)}
          />
        </label>
      </div>

      <div>
        <label className={label}>Photos (optional, up to 20)</label>
        <input type="file" name="photos" accept="image/*" multiple className={field} />
      </div>

      <div className="space-y-3 rounded-2xl border border-hair bg-white p-5 text-sm">
        <label className="flex items-start gap-3">
          <input type="checkbox" name="allowHumor" defaultChecked className="mt-1" />
          <span>We allow the AI to use humorous observations from our messages.</span>
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" name="consent" required className="mt-1" />
          <span>We consent to processing the uploaded chat solely to generate this product. *</span>
        </label>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-full bg-ember px-8 py-4 font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {busy ? 'Uploading…' : 'Create my archive'}
      </button>
    </form>
  );
}
