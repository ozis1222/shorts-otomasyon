/** Shared LocalStorageProvider rooted at the data dir (spec §32). */
import { LocalStorageProvider } from '../src/integrations/storage-provider.js';
import { webEnv } from '../lib/env.js';
import { join } from 'node:path';

let storage: LocalStorageProvider | null = null;

export function getStorage(): LocalStorageProvider {
  if (!storage) storage = new LocalStorageProvider(join(webEnv.dataDir, 'storage'), webEnv.appSecret);
  return storage;
}

export const keys = {
  chat: (orderId: string) => `orders/${orderId}/uploads/chat.txt`,
  photo: (orderId: string, n: number) => `orders/${orderId}/uploads/photo-${n}.jpg`,
  asset: (orderId: string, rel: string) => `orders/${orderId}/archive/${rel}`,
  zip: (orderId: string) => `orders/${orderId}/the-us-archive-${orderId}.zip`,
};
