-- The Us Archive — relational schema (node:sqlite for dev; the same DDL maps
-- cleanly to Postgres/Supabase for production).
--
-- Design note (spec §31): we deliberately do NOT store the millions of raw
-- messages long-term. Only the compact statistics + the canonical relationship
-- profile are persisted; the raw .txt lives on disk and is purged after the
-- retention window.

CREATE TABLE IF NOT EXISTS orders (
  id                TEXT PRIMARY KEY,
  secure_token      TEXT NOT NULL UNIQUE,
  source            TEXT NOT NULL DEFAULT 'mock',      -- mock | etsy
  external_id       TEXT,                              -- Etsy receipt id
  package_id        TEXT NOT NULL,
  buyer_email       TEXT,
  buyer_name        TEXT,
  state             TEXT NOT NULL DEFAULT 'WAITING_UPLOAD',
  stage             TEXT NOT NULL DEFAULT 'CREATED',   -- pipeline stage
  progress          INTEGER NOT NULL DEFAULT 0,        -- 0..100
  error             TEXT,
  theme             TEXT NOT NULL DEFAULT 'light',
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  uploaded_at       TEXT,
  delivered_at      TEXT,
  expires_at        TEXT,
  raw_deleted_at    TEXT
);

CREATE TABLE IF NOT EXISTS onboarding (
  order_id          TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  partner_a         TEXT NOT NULL,
  partner_b         TEXT NOT NULL,
  language          TEXT NOT NULL DEFAULT 'en',
  tone              TEXT NOT NULL DEFAULT 'balanced',
  relationship_start TEXT,
  anniversary       TEXT,
  first_date        TEXT,
  first_trip        TEXT,
  wedding_date      TEXT,
  current_city      TEXT,
  allow_humor       INTEGER NOT NULL DEFAULT 1,
  consent           INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploads (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  kind              TEXT NOT NULL,                     -- chat | photo
  filename          TEXT NOT NULL,
  storage_key       TEXT NOT NULL,
  bytes             INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
  order_id          TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  statistics_json   TEXT NOT NULL,
  profile_json      TEXT NOT NULL,
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  kind              TEXT NOT NULL,                     -- pdf | zip | story | instagram | wallpaper | poster | fingerprint
  filename          TEXT NOT NULL,
  storage_key       TEXT NOT NULL,
  bytes             INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  status            TEXT NOT NULL DEFAULT 'queued',    -- queued | running | done | failed
  attempts          INTEGER NOT NULL DEFAULT 0,
  last_error        TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_logs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          TEXT,
  to_addr           TEXT NOT NULL,
  template          TEXT NOT NULL,
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          TEXT,
  event             TEXT NOT NULL,
  detail            TEXT,
  created_at        TEXT NOT NULL
);

-- Single-row store for integration secrets/tokens (e.g. Etsy OAuth tokens).
CREATE TABLE IF NOT EXISTS integrations (
  name              TEXT PRIMARY KEY,                  -- 'etsy'
  data_json         TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_state ON orders(state);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_uploads_order ON uploads(order_id);
CREATE INDEX IF NOT EXISTS idx_assets_order ON assets(order_id);
