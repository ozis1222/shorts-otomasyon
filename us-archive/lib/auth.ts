/** Minimal admin auth: a signed cookie derived from ADMIN_PASSWORD. */
import { createHmac, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';
import { webEnv } from './env.js';

const COOKIE = 'ua_admin';

function token(): string {
  return createHmac('sha256', webEnv.appSecret).update(`admin:${webEnv.adminPassword}`).digest('base64url');
}

export function checkPassword(password: string): boolean {
  const a = Buffer.from(password);
  const b = Buffer.from(webEnv.adminPassword);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function sessionCookie() {
  return { name: COOKIE, value: token() };
}

export function isAdmin(): boolean {
  const c = cookies().get(COOKIE)?.value;
  if (!c) return false;
  const expected = token();
  const a = Buffer.from(c);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
