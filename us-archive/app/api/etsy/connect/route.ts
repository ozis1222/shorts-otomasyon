import { NextResponse } from 'next/server';
import { isAdmin } from '@/lib/auth';
import { getAuthUrl } from '@/server/etsy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  if (!isAdmin()) return NextResponse.redirect(new URL('/admin/login', req.url), 303);
  try {
    return NextResponse.redirect(getAuthUrl(), 303);
  } catch (err) {
    return NextResponse.redirect(new URL(`/admin?etsy_error=${encodeURIComponent(String(err))}`, req.url), 303);
  }
}
