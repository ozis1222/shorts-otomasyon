/** Web-app runtime configuration (separate from the engine's src/config). */
import { join } from 'node:path';

function str(name: string, fallback: string): string {
  const v = process.env[name];
  return v === undefined || v === '' ? fallback : v;
}

export const webEnv = {
  baseUrl: str('APP_BASE_URL', 'http://localhost:3000'),
  /** Root directory for the SQLite DB, uploads and generated archives. */
  dataDir: str('DATA_DIR', join(process.cwd(), 'data')),
  /** Secret for signing admin sessions and download URLs. Change in production. */
  appSecret: str('APP_SECRET', 'dev-insecure-secret-change-me'),
  adminPassword: str('ADMIN_PASSWORD', 'admin'),

  orderProvider: str('ORDER_PROVIDER', 'mock') as 'mock' | 'etsy',
  emailProvider: str('EMAIL_PROVIDER', 'console') as 'console' | 'resend' | 'smtp',
  resendApiKey: str('RESEND_API_KEY', ''),
  emailFrom: str('EMAIL_FROM', 'The Us Archive <hello@theusarchive.test>'),

  etsy: {
    apiKey: str('ETSY_API_KEY', ''),
    apiSecret: str('ETSY_API_SECRET', ''),
    shopId: str('ETSY_SHOP_ID', ''),
    redirectUri: str('ETSY_REDIRECT_URI', 'http://localhost:3000/api/etsy/callback'),
    /** Map Etsy listing IDs to our package tier ids. JSON string. */
    listingMap: str('ETSY_LISTING_MAP', '{}'),
  },

  /** Days before a customer's raw upload is auto-purged (mirrors engine config). */
  retentionDays: Number(str('RAW_DATA_RETENTION_DAYS', '7')),
} as const;

export const ordersDir = () => join(webEnv.dataDir, 'orders');
export const dbPath = () => join(webEnv.dataDir, 'us-archive.db');
