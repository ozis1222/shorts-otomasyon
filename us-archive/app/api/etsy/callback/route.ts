import { NextResponse } from 'next/server';
import { handleCallback } from '@/server/etsy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  const url = new URL(req.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  if (!code || !state) return NextResponse.redirect(new URL('/admin?etsy_error=missing_code', req.url), 303);
  try {
    await handleCallback(code, state);
    return NextResponse.redirect(new URL('/admin?etsy=connected', req.url), 303);
  } catch (err) {
    return NextResponse.redirect(new URL(`/admin?etsy_error=${encodeURIComponent(String(err))}`, req.url), 303);
  }
}
