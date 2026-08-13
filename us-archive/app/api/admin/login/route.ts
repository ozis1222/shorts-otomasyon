import { NextResponse } from 'next/server';
import { checkPassword, sessionCookie } from '@/lib/auth';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  const form = await req.formData();
  const password = String(form.get('password') || '');
  if (!checkPassword(password)) {
    return NextResponse.redirect(new URL('/admin/login?error=1', req.url), 303);
  }
  const res = NextResponse.redirect(new URL('/admin', req.url), 303);
  const c = sessionCookie();
  res.cookies.set(c.name, c.value, { httpOnly: true, sameSite: 'lax', path: '/', maxAge: 60 * 60 * 24 * 7 });
  return res;
}
