import { NextResponse } from 'next/server';
import { Orders, Assets } from '@/db/repo';
import { getStorage } from '@/server/storage';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MIME: Record<string, string> = {
  pdf: 'application/pdf',
  png: 'image/png',
  svg: 'image/svg+xml',
  zip: 'application/zip',
  json: 'application/json',
};

/**
 * Serves a delivered asset. The unguessable order token is the capability;
 * the file must belong to that order. Files are private — never public URLs.
 */
export async function GET(_req: Request, { params }: { params: { token: string; file: string[] } }) {
  const order = Orders.byToken(params.token);
  if (!order) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  if (order.state !== 'DELIVERED') return NextResponse.json({ error: 'Not ready' }, { status: 409 });

  const filename = params.file.join('/');
  const asset = Assets.byOrderAndFile(order.id, filename);
  if (!asset) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  let data: Buffer;
  try {
    data = await getStorage().get(asset.storage_key);
  } catch {
    return NextResponse.json({ error: 'File missing' }, { status: 410 });
  }
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const base = filename.split('/').pop() || 'file';
  const disposition = asset.kind === 'zip' || asset.kind === 'pdf' ? 'attachment' : 'inline';
  return new NextResponse(data as any, {
    headers: {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Content-Disposition': `${disposition}; filename="${base}"`,
      'Cache-Control': 'private, max-age=3600',
    },
  });
}
