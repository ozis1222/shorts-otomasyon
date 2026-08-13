# THE US ARCHIVE

**Your relationship, decoded.** Turn years of WhatsApp conversations into a
one-of-a-kind, premium digital archive — a 25–40 page editorial magazine, a
generative *Relationship Fingerprint*, shareable social cards, and phone/desktop
wallpapers — automatically, from a single chat export.

This repository contains **both**:

1. the **product engine** — the deterministic + AI pipeline that turns a raw
   `.txt` export into a finished, packaged deliverable; and
2. the **full web app / SaaS shell** — a Next.js application with a landing
   page, customer onboarding + upload, a customer portal (progress, preview,
   download, *delete my data*), a seller admin dashboard, a database, a job
   queue, transactional email, and a **real Etsy integration** that turns paid
   orders into archives automatically.

It runs **end-to-end offline** (no API key, no Etsy account) via a built-in mock
AI provider and a mock order source, so you can click through the entire flow
today.

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

## Run the web app (the actual product)

```bash
cp .env.example .env      # defaults work as-is for local dev
npm run dev               # web app  → http://localhost:3000
npm run worker            # in a second terminal: processes the job queue
```

Then:

1. Open **http://localhost:3000** — the landing page.
2. Go to **/admin** (password `admin` by default) — the seller dashboard.
3. Click **“Test order (auto-run Alex & Mia)”** — this creates a mock order,
   fills onboarding, queues it, and the worker builds the full archive. Watch
   the order move through the pipeline; open it to preview and download.
4. Or click **“Empty order (get upload link)”** to walk the real customer path:
   open the link, fill the form, upload a WhatsApp `.txt`, and follow the live
   progress to download.

Everything above works with **no external accounts**. Connecting Etsy and going
live is the "Go live" section below.

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

# Web app (Next.js App Router)
app/              landing · onboarding/[token] · order/[token] · admin/* · api/*
components/       OnboardingForm · OrderPortal · AdminActions (client)
db/               schema.sql · connection (node:sqlite) · typed repos
server/           orders · process-order · queue · worker-loop · email · etsy
lib/              env · auth
```

The web app imports the engine directly — one package, no service split
(spec §40: "no microservice hell"). Heavy work (AI + Playwright PDF) runs in the
background worker/queue, never inside an HTTP request.

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

## Go live (Etsy + deploy)

The whole app runs locally with no accounts. To actually **sell**, a few steps
require *your* Etsy account and hosting — they can't be done for you, but the
code is ready for them:

**1. Etsy app + credentials**
- Create an app at the [Etsy Developer portal](https://www.etsy.com/developers/)
  and request the **`transactions_r`** and **`email_r`** scopes (needed to read
  paid receipts and buyer email). Commercial use requires Etsy's app approval.
- Put the keystring/secret and your numeric shop id in `.env`:
  `ETSY_API_KEY`, `ETSY_API_SECRET`, `ETSY_SHOP_ID`.
- Set `ETSY_REDIRECT_URI` to `https://yourdomain.com/api/etsy/callback` and add
  that exact URL to your Etsy app's allowed redirect URIs.
- Map your listings to tiers: `ETSY_LISTING_MAP={"<listingId>":"full", …}`.
- Set `ORDER_PROVIDER=etsy`.

**2. Connect + sync**
- Deploy, open `/admin`, and click **Connect Etsy** (OAuth2 + PKCE — tokens are
  stored server-side and auto-refreshed).
- Click **Sync Etsy orders**, or let the cron endpoint do it automatically. Each
  new paid receipt becomes an order and the buyer gets an upload-link email.

**3. Production settings**
- `APP_SECRET` → long random string · `ADMIN_PASSWORD` → strong password.
- `APP_BASE_URL=https://yourdomain.com`.
- `EMAIL_PROVIDER=resend` + `RESEND_API_KEY` + a verified `EMAIL_FROM` domain.
- `AI_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` for the best semantic quality.

**4. Run the worker**
- Always-on host (Render/Railway/Fly/VPS): run `npm run build && npm start` for
  the web and `npm run worker` as a second process. Point a scheduler at
  `GET /api/cron?key=$APP_SECRET` every minute as a safety net (it also runs the
  Etsy sync + retention purge).
- Serverless (Vercel): the app deploys as-is; because PDF rendering needs
  headless Chromium, run the **worker** on a small always-on box (or a container)
  and keep the Vercel deploy for the UI + API. `DATA_DIR` must point at
  persistent storage; for multi-instance, swap `LocalStorageProvider` for the
  S3/Supabase implementation of the same interface.

> We only use Etsy's official, sanctioned API. We never scrape or bypass
> endpoints Etsy doesn't permit (spec §28).

### Moving off SQLite

Dev uses Node's built-in `node:sqlite` (zero native deps). The DDL in
`db/schema.sql` is Postgres-compatible; point `db/index.ts` at Supabase/Postgres
and the repos in `db/repo.ts` carry over with minimal change. Raw messages are
intentionally **not** stored — only the compact statistics + canonical profile
are persisted (spec §31).

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Executable doesn't exist` (Chromium) | This env ships Chromium; `src/render/browser.ts` auto-locates it under `PLAYWRIGHT_BROWSERS_PATH`. Don't run `playwright install`. |
| PDF fonts look plain | `Fraunces`/`Inter` fall back to Georgia/system fonts if not installed — still editorial. Install the Google Fonts for the exact look. |
| `need at least 2 participants` | The export had one sender or an unrecognized format; check it's a WhatsApp `.txt` export. |
| Output validation error | A section produced `undefined`/`null` — the pipeline fails loudly by design rather than shipping broken output. |
| Anthropic errors | Verify `ANTHROPIC_API_KEY`; the provider retries with backoff, then throws. |
