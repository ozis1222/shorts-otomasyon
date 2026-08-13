# THE US ARCHIVE

**Your relationship, decoded.** Turn years of WhatsApp conversations into a
one-of-a-kind, premium digital archive — a 25–40 page editorial magazine, a
generative *Relationship Fingerprint*, shareable social cards, and phone/desktop
wallpapers — automatically, from a single chat export.

This repository contains the **product engine**: the deterministic + AI pipeline
that turns a raw `.txt` export into a finished, packaged deliverable. It runs
**end-to-end offline** (no API key) via a built-in mock AI provider, so you can
see the full output today.

```
WhatsApp .txt ─▶ parse ─▶ deterministic statistics ─▶ AI semantic analysis
   ─▶ Relationship Profile (canonical JSON) ─▶ PDF magazine + fingerprint
   ─▶ social cards + wallpapers ─▶ ZIP ─▶ secure delivery
```

---

## Quick start (30 seconds)

```bash
cd us-archive
npm install          # Chromium is already present in this environment
npm run demo         # generates the synthetic "Alex & Mia" archive end-to-end
```

Open the results in `output/demo/archive/`:

| File | What it is |
| --- | --- |
| `archive.pdf` | 24-page editorial magazine (dynamic length) |
| `relationship-fingerprint.png` / `.svg` | signature generative artwork |
| `relationship-fingerprint-poster.png` | framed poster (1080×1350) |
| `stories/` | 10× Instagram/TikTok story cards (1080×1920) |
| `instagram/` | 5× Instagram cards (1080×1350) |
| `wallpapers/` | phone (1080×1920) + desktop (1920×1080) |
| `relationship-profile.json` | the canonical profile everything is rendered from |
| `../the-us-archive-DEMO-ALEX-MIA.zip` | the full delivery bundle |

Try other tiers/themes: `npm run demo -- mini dark` · `npm run demo -- vault light`.

---

## Architecture

Two layers, by design:

1. **Deterministic core** — the parser and *all numbers* (message counts,
   percentages, emoji/word frequencies, time distributions, sessions, quiet
   periods…) are computed in plain TypeScript. The LLM never counts, so numbers
   can't be hallucinated (spec principle §2).
2. **Semantic layer** — the model only does *meaning*: inside jokes, era names,
   award citations, memorable-moment selection, cover copy. It receives
   **deterministic candidates**, not the raw chat in bulk, which cuts cost and
   hallucination. Every stage has a Zod schema and retry.

```
src/
  parser/         robust WhatsApp export parser (many dialects) → normalized JSON
  stats/          deterministic statistics + DNA/archetype signal scoring
  privacy/        SAFE/NORMAL content filtering, retention rules
  ai/             provider abstraction (anthropic | mock) + versioned prompts/
  profile/        canonical Relationship Profile (Zod schema)
  fingerprint/    deterministic seed → generative SVG art
  render/         design system, SVG charts, magazine HTML → PDF, social assets
  packaging/      ZIP bundling
  synthetic/      seeded fake-chat generator (test data)
  pipeline/       analyze() + idempotent, resumable orchestrator
  integrations/   OrderProvider (mock|etsy) · EmailProvider · StorageProvider
  cli/            demo · synthetic · pipeline
test/             parser · statistics · privacy · profile+render
```

### The canonical Relationship Profile

Everything (PDF, cards, fingerprint) renders from **one** JSON produced once by
the pipeline (`src/profile/schema.ts`). The renderer never re-queries the model.

---

## Environment variables

Copy `.env.example` to `.env`. Every value has a safe default; the demo needs
none. Highlights:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_PROVIDER` | `mock` | `mock` (offline) or `anthropic` |
| `ANTHROPIC_API_KEY` | — | required only for `anthropic` |
| `ANALYSIS_MODEL` / `SYNTHESIS_MODEL` | haiku / opus | cheap→expensive escalation |
| `RAW_DATA_RETENTION_DAYS` | `7` | auto-delete raw chats after delivery |
| `CONTENT_SENSITIVITY` | `SAFE` | strip sensitive content from output |
| `SESSION_GAP_HOURS` | `6` | conversation-session threshold |
| `INSIDE_JOKE_CONFIDENCE` | `0.6` | drop low-confidence inferred content |
| `BRAND_WATERMARK` | `true` | toggle the "Made with…" tag |

---

## Anthropic setup (optional — for real semantic quality)

```bash
export AI_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
npm run demo
```

The provider abstraction (`src/ai/provider.ts`) starts with Anthropic;
OpenAI/Gemini can be added by implementing the same `ModelProvider` interface.
Prompts live in `src/ai/prompts/` — versioned, each with a Zod output schema and
JSON-parse retry with backoff.

---

## Running analysis on a real chat

Export a WhatsApp chat (**⋮ → More → Export chat → Without media**, or with
media — media placeholders are handled), then:

```bash
npm run run:pipeline -- --file=my-chat.txt --a="Alex" --b="Mia" \
  --package=full --theme=light --start=2022-06-15
```

Output lands in `output/<orderId>/`. The pipeline is **idempotent**: each stage
persists its artifact, so re-running resumes rather than restarting. Force a
clean rebuild with `--force=true`.

## Synthetic chat generation (test data)

```bash
npm run generate:synthetic -- --a=Alex --b=Mia --months=36 --messages=25000 \
  --seed=42 --out=fake.txt
```

Seeded, so the same seed always yields the same chat. Used by the demo and tests.

---

## Testing

```bash
npm test         # vitest: parser, statistics, privacy, profile+render smoke
npm run typecheck
```

Covered: format auto-detection (DMY/MDY, 12h/24h, bracketed/dashed), multiline,
media/voice/deleted classification, Turkish/Unicode; deterministic stats;
SAFE-mode redaction & retention; schema validity; fingerprint determinism; and
output validation (no `undefined`/`null`/placeholder ever ships).

---

## Privacy (a core feature, not an afterthought)

- Raw conversations are **auto-deleted** `RAW_DATA_RETENTION_DAYS` after
  delivery; customers can also delete immediately (`deleteRawData`).
- **SAFE** mode (default) strips phone numbers, emails, IDs, financial, health
  and explicit content from anything reaching the deliverable *or* the LLM.
- Raw message content is **never logged** — logs carry `orderId`, stage,
  counts, timings only.
- The delivery ZIP contains only the deliverable (the raw `.txt` is kept
  outside it and purged on schedule).
- Storage paths are private; delivery uses short-lived **signed URLs**, never
  public links (`src/integrations/storage-provider.ts`).
- Chat content is never sent to analytics.

## AI safety

The prompts forbid infidelity claims, mental-health/personality diagnoses,
"toxic" labels, future prediction, and "who loves whom more". Framing stays
playful ("Based on your patterns…"). The Relationship DNA carries a visible
*"For entertainment and memory-keeping purposes."* disclaimer.

---

## Package tiers

Config-driven in `src/config/packages.ts` (`mini`, `full`, `vault`) — sections
and asset counts are data, not hard-coded. Add a tier by editing that file.

## Etsy integration

Modular via `OrderProvider` (`src/integrations/order-provider.ts`).
`MockOrderProvider` drives development and the demo today; `EtsyOrderProvider`
is a clearly-marked stub for the official Etsy Open API v3 (OAuth2). We do **not**
scrape or bypass unsanctioned endpoints. Secure per-order tokens are 32-byte
URL-safe randoms with expiry.

---

## Deployment

The engine is a Node library + CLI and runs anywhere Node 20+ and headless
Chromium are available. `npm run demo` is the reference invocation. The heavy
work (parse → AI → render) is designed to run as a background job per order, not
inside an HTTP request; the orchestrator's persisted stages make it safe to run
under any queue (BullMQ/Redis or a DB-backed queue).

## Roadmap (SaaS layer)

The product engine above is complete and tested. The customer-facing SaaS shell
is scaffolded at the interface level and is the next build phase:

- **Web app** (Next.js): landing page, mobile-first onboarding + upload, customer
  portal (progress, preview, download, *delete my data*), admin dashboard
  (order states, per-stage pipeline view, retry).
- **Persistence** (Postgres/Supabase): orders, tokens, jobs, profiles, assets,
  audit logs. Raw messages are intentionally **not** stored long-term — only the
  compact statistics + canonical profile are retained.
- **Queue/email/storage**: concrete `BullMQ`, `Resend`/SMTP, and `S3`/Supabase
  implementations of the interfaces already present in `src/integrations/`.
- **i18n**: English + Türkçe; AI output language follows onboarding selection.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Executable doesn't exist` (Chromium) | This env ships Chromium; `src/render/browser.ts` auto-locates it under `PLAYWRIGHT_BROWSERS_PATH`. Don't run `playwright install`. |
| PDF fonts look plain | `Fraunces`/`Inter` fall back to Georgia/system fonts if not installed — still editorial. Install the Google Fonts for the exact look. |
| `need at least 2 participants` | The export had one sender or an unrecognized format; check it's a WhatsApp `.txt` export. |
| Output validation error | A section produced `undefined`/`null` — the pipeline fails loudly by design rather than shipping broken output. |
| Anthropic errors | Verify `ANTHROPIC_API_KEY`; the provider retries with backoff, then throws. |
