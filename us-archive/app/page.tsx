import Link from 'next/link';
import { PACKAGES } from '@/src/config/packages';

export const dynamic = 'force-static';

function Section({ id, children, className = '' }: { id?: string; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-5xl px-6 ${className}`}>
      {children}
    </section>
  );
}

export default function Landing() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      {/* Nav */}
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <span className="text-sm font-bold uppercase tracking-[0.25em] text-ember">The Us Archive</span>
        <nav className="hidden gap-8 text-sm text-inksoft sm:flex">
          <a href="#how" className="hover:text-ink">How it works</a>
          <a href="#inside" className="hover:text-ink">What&apos;s inside</a>
          <a href="#packages" className="hover:text-ink">Packages</a>
          <a href="#privacy" className="hover:text-ink">Privacy</a>
        </nav>
      </header>

      {/* Hero */}
      <Section className="pt-16 pb-24 text-center">
        <p className="mb-6 text-xs font-bold uppercase tracking-[0.3em] text-ember">A one-of-a-kind digital keepsake</p>
        <h1 className="font-editorial text-6xl leading-[1.02] sm:text-7xl">
          Your relationship.
          <br />
          Decoded.
        </h1>
        <p className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-inksoft">
          Turn years of conversations into a premium, personalized digital archive — a beautiful magazine, a
          generative fingerprint that&apos;s uniquely yours, and shareable cards. Thousands of messages. One story.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a href="#packages" className="rounded-full bg-ember px-8 py-4 font-semibold text-white transition hover:opacity-90">
            Create Your Archive
          </a>
          <a href="#inside" className="rounded-full border border-hair px-8 py-4 font-semibold text-ink transition hover:border-ink">
            See what&apos;s inside
          </a>
        </div>
        <div className="mx-auto mt-16 grid max-w-3xl grid-cols-3 gap-6 text-center">
          {[
            ['25–40', 'page magazine'],
            ['1 of 1', 'relationship fingerprint'],
            ['18+', 'shareable assets'],
          ].map(([n, l]) => (
            <div key={l} className="rounded-2xl border border-hair bg-white/60 p-6">
              <div className="font-editorial text-3xl">{n}</div>
              <div className="mt-1 text-xs uppercase tracking-wide text-inksoft">{l}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* How it works */}
      <Section id="how" className="py-20">
        <h2 className="font-editorial text-4xl">How it works</h2>
        <div className="mt-10 grid gap-8 sm:grid-cols-4">
          {[
            ['1', 'Order', 'Buy your archive on Etsy. You get a private, secure link — no account needed.'],
            ['2', 'Upload', 'Export your WhatsApp chat as a .txt and drop it in. Add photos if you like.'],
            ['3', 'We build it', 'We compute the real numbers and craft a personalized story — usually in minutes.'],
            ['4', 'Download', 'Get your magazine, fingerprint, cards and wallpapers. Delete your chat anytime.'],
          ].map(([n, t, d]) => (
            <div key={n}>
              <div className="font-editorial text-2xl text-ember">{n}</div>
              <h3 className="mt-2 font-semibold">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-inksoft">{d}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* What's inside */}
      <Section id="inside" className="py-20">
        <h2 className="font-editorial text-4xl">What&apos;s inside</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {[
            ['Our Numbers', 'Every message, word, emoji and late-night text — counted, never guessed.'],
            ['Relationship DNA', 'A playful signature blend across eight dimensions. For fun, not diagnosis.'],
            ['Who Does What', 'Who texts more, starts more, asks more — the honest scoreboard.'],
            ['The Couple Dictionary', 'Your inside jokes and made-up words, defined.'],
            ['Relationship Fingerprint', 'A generative artwork drawn from the shape of your chats. One of one.'],
            ['Awards & Eras', 'Late Night Champion, your chapters, memorable moments kept verbatim.'],
          ].map(([t, d]) => (
            <div key={t} className="rounded-2xl border border-hair bg-white p-6">
              <h3 className="font-editorial text-xl">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-inksoft">{d}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Packages */}
      <Section id="packages" className="py-20">
        <h2 className="font-editorial text-4xl">Packages</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {Object.values(PACKAGES).map((p) => (
            <div key={p.id} className="flex flex-col rounded-2xl border border-hair bg-white p-8">
              <h3 className="font-editorial text-2xl">{p.name}</h3>
              <p className="mt-2 text-sm text-inksoft">{p.tagline}</p>
              <ul className="mt-6 flex-1 space-y-2 text-sm">
                <li>{p.sections.length} magazine sections</li>
                <li>{p.assets.storyCards} story cards</li>
                <li>{p.assets.instagramCards} Instagram cards</li>
                <li>{p.assets.phoneWallpapers + p.assets.desktopWallpapers} wallpapers</li>
                {p.assets.fingerprintPoster && <li>Fingerprint poster</li>}
              </ul>
              <a
                href="https://www.etsy.com"
                className="mt-8 rounded-full bg-ink px-6 py-3 text-center font-semibold text-white transition hover:opacity-90"
              >
                Buy on Etsy
              </a>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-inksoft">
          Already ordered? Use the private link from your confirmation email to upload your chat.
        </p>
      </Section>

      {/* Privacy */}
      <Section id="privacy" className="py-20">
        <div className="rounded-3xl border border-hair bg-white p-10">
          <h2 className="font-editorial text-4xl">Privacy, by design</h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            {[
              ['Your chat is yours', 'It is used only to build your archive — never sold, never used to train anything.'],
              ['Auto-deleted', 'Your raw chat is permanently deleted after delivery. You can also delete it instantly.'],
              ['Sensitive content filtered', 'Phone numbers, addresses, IDs and private details are kept out of the product.'],
              ['Private links only', 'No public URLs. Downloads use secure, expiring links.'],
            ].map(([t, d]) => (
              <div key={t}>
                <h3 className="font-semibold">{t}</h3>
                <p className="mt-1 text-sm leading-relaxed text-inksoft">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* FAQ */}
      <Section className="py-20">
        <h2 className="font-editorial text-4xl">FAQ</h2>
        <div className="mt-8 space-y-6">
          {[
            ['How do I export my WhatsApp chat?', 'Open the chat → ⋮ / More → Export chat → Without media (or with media — placeholders are handled), then upload the .txt.'],
            ['Is this a personality test?', 'No. The Relationship DNA and archetypes are for entertainment and memory-keeping — not psychological assessment.'],
            ['What if we barely have photos?', 'That&apos;s fine — the archive is designed to look beautiful with zero photos.'],
            ['Which languages are supported?', 'English and Türkçe today; the AI output follows the language you choose.'],
          ].map(([q, a]) => (
            <div key={q} className="border-b border-hair pb-6">
              <h3 className="font-semibold">{q}</h3>
              <p className="mt-2 text-sm leading-relaxed text-inksoft" dangerouslySetInnerHTML={{ __html: a }} />
            </div>
          ))}
        </div>
      </Section>

      <footer className="border-t border-hair py-10 text-center text-xs text-inksoft">
        <p className="font-bold uppercase tracking-[0.25em] text-ember">The Us Archive</p>
        <p className="mt-2">Your conversations became your story.</p>
        <p className="mt-4">
          <Link href="/admin" className="hover:text-ink">Seller dashboard</Link>
        </p>
      </footer>
    </main>
  );
}
