/**
 * Object-storage abstraction (spec §32). Local filesystem for development;
 * S3/Supabase implement the same interface. Paths are always private — public
 * URLs are never minted; downloads go through short-lived signed URLs.
 */
import { mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { existsSync } from 'node:fs';
import { createHmac } from 'node:crypto';

export interface StorageProvider {
  readonly name: string;
  put(key: string, data: Buffer | string): Promise<void>;
  get(key: string): Promise<Buffer>;
  remove(key: string): Promise<void>;
  /** Time-limited signed URL for a private object. */
  signedUrl(key: string, ttlSeconds: number): Promise<string>;
}

export class LocalStorageProvider implements StorageProvider {
  readonly name = 'local';
  constructor(private readonly root: string, private readonly secret = 'dev-secret') {}

  private path(key: string): string {
    return join(this.root, key);
  }
  async put(key: string, data: Buffer | string): Promise<void> {
    const p = this.path(key);
    await mkdir(dirname(p), { recursive: true });
    await writeFile(p, data);
  }
  async get(key: string): Promise<Buffer> {
    return readFile(this.path(key));
  }
  async remove(key: string): Promise<void> {
    const p = this.path(key);
    if (existsSync(p)) await rm(p);
  }
  async signedUrl(key: string, ttlSeconds: number): Promise<string> {
    const exp = Date.now() + ttlSeconds * 1000;
    const sig = createHmac('sha256', this.secret).update(`${key}:${exp}`).digest('base64url');
    return `/files/${encodeURIComponent(key)}?exp=${exp}&sig=${sig}`;
  }

  /** Verify a signed URL's signature + expiry (used by the download route). */
  verify(key: string, exp: number, sig: string): boolean {
    if (Date.now() > exp) return false;
    const expected = createHmac('sha256', this.secret).update(`${key}:${exp}`).digest('base64url');
    return sig === expected;
  }
}
