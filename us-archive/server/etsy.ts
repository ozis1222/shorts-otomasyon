/**
 * Real Etsy Open API v3 integration (spec §28).
 *
 * Flow: shop owner connects once via OAuth2 (authorization code + PKCE); we
 * store the access/refresh tokens; syncOrders() pulls new receipts and turns
 * each into an internal order. We only ever use the official, sanctioned API —
 * no scraping, no bypassing endpoints Etsy doesn't permit.
 *
 * Requires (set by the shop owner — see README "Go live"):
 *   ETSY_API_KEY, ETSY_API_SECRET, ETSY_SHOP_ID, ETSY_REDIRECT_URI,
 *   ETSY_LISTING_MAP  (JSON: { "<listing_id>": "<package_id>" })
 */
import { createHash, randomBytes } from 'node:crypto';
import { webEnv } from '../lib/env.js';
import { Integrations, Orders, Logs } from '../db/repo.js';
import { createOrder } from './orders.js';

const OAUTH_CONNECT = 'https://www.etsy.com/oauth/connect';
const OAUTH_TOKEN = 'https://api.etsy.com/v3/public/oauth/token';
const API = 'https://openapi.etsy.com/v3/application';
const SCOPES = 'transactions_r email_r';

function b64url(buf: Buffer): string {
  return buf.toString('base64url');
}

export function isConfigured(): boolean {
  return Boolean(webEnv.etsy.apiKey && webEnv.etsy.apiSecret && webEnv.etsy.shopId);
}

export function isConnected(): boolean {
  return Boolean(Integrations.get('etsy')?.access_token);
}

/** Build the consent URL and stash the PKCE verifier + state for the callback. */
export function getAuthUrl(): string {
  if (!isConfigured()) throw new Error('Etsy is not configured (missing ETSY_API_KEY/SECRET/SHOP_ID).');
  const verifier = b64url(randomBytes(48));
  const challenge = b64url(createHash('sha256').update(verifier).digest());
  const state = b64url(randomBytes(16));
  Integrations.set('etsy_oauth', { verifier, state });
  const url = new URL(OAUTH_CONNECT);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('client_id', webEnv.etsy.apiKey);
  url.searchParams.set('redirect_uri', webEnv.etsy.redirectUri);
  url.searchParams.set('scope', SCOPES);
  url.searchParams.set('state', state);
  url.searchParams.set('code_challenge', challenge);
  url.searchParams.set('code_challenge_method', 'S256');
  return url.toString();
}

export async function handleCallback(code: string, state: string): Promise<void> {
  const stash = Integrations.get('etsy_oauth');
  if (!stash || stash.state !== state) throw new Error('Invalid OAuth state');
  const res = await fetch(OAUTH_TOKEN, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: webEnv.etsy.apiKey,
      redirect_uri: webEnv.etsy.redirectUri,
      code,
      code_verifier: stash.verifier,
    }),
  });
  if (!res.ok) throw new Error(`Etsy token exchange failed: ${res.status} ${await res.text()}`);
  const tok = (await res.json()) as { access_token: string; refresh_token: string; expires_in: number };
  Integrations.set('etsy', {
    access_token: tok.access_token,
    refresh_token: tok.refresh_token,
    expires_at: Date.now() + tok.expires_in * 1000,
  });
  Logs.audit(null, 'etsy_connected');
}

async function accessToken(): Promise<string> {
  const t = Integrations.get('etsy');
  if (!t?.access_token) throw new Error('Etsy not connected — run OAuth first.');
  if (Date.now() < t.expires_at - 60_000) return t.access_token;
  // Refresh.
  const res = await fetch(OAUTH_TOKEN, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: webEnv.etsy.apiKey,
      refresh_token: t.refresh_token,
    }),
  });
  if (!res.ok) throw new Error(`Etsy token refresh failed: ${res.status}`);
  const tok = (await res.json()) as { access_token: string; refresh_token: string; expires_in: number };
  Integrations.set('etsy', {
    access_token: tok.access_token,
    refresh_token: tok.refresh_token,
    expires_at: Date.now() + tok.expires_in * 1000,
  });
  return tok.access_token;
}

async function apiGet(path: string): Promise<any> {
  const token = await accessToken();
  const res = await fetch(`${API}${path}`, {
    headers: { 'x-api-key': webEnv.etsy.apiKey, Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Etsy API ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

function listingMap(): Record<string, string> {
  try {
    return JSON.parse(webEnv.etsy.listingMap);
  } catch {
    return {};
  }
}

/** Pull recent paid receipts and create an order for each new one. */
export async function syncOrders(limit = 25): Promise<{ created: number; scanned: number }> {
  const map = listingMap();
  const data = await apiGet(`/shops/${webEnv.etsy.shopId}/receipts?was_paid=true&limit=${limit}`);
  const receipts: any[] = data.results ?? [];
  let created = 0;
  for (const r of receipts) {
    const externalId = String(r.receipt_id);
    if (Orders.byExternalId(externalId)) continue;
    // Determine package from the first mapped listing on the receipt.
    const listingIds: string[] = (r.transactions ?? []).map((t: any) => String(t.listing_id));
    const pkg = listingIds.map((id) => map[id]).find(Boolean) ?? 'full';
    await createOrder({
      source: 'etsy',
      externalId,
      packageId: pkg,
      buyerEmail: r.buyer_email ?? null,
      buyerName: r.name ?? null,
    });
    created++;
  }
  Logs.audit(null, 'etsy_sync', `scanned=${receipts.length} created=${created}`);
  return { created, scanned: receipts.length };
}
