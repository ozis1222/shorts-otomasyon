/**
 * Shared headless-Chromium access via playwright-core, pointed at the browser
 * that ships in this environment (no `playwright install` needed). Falls back to
 * scanning PLAYWRIGHT_BROWSERS_PATH for the chrome binary if the bundled
 * resolver can't find a matching revision.
 */
import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { chromium, type Browser } from 'playwright-core';

let browserPromise: Promise<Browser> | null = null;

function findChromeExecutable(): string | undefined {
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  if (!existsSync(root)) return undefined;
  const candidates: string[] = [];
  for (const entry of readdirSync(root)) {
    if (!/chromium/i.test(entry)) continue;
    for (const rel of [
      'chrome-linux/chrome',
      'chrome-linux/headless_shell',
    ]) {
      const p = join(root, entry, rel);
      if (existsSync(p)) candidates.push(p);
    }
  }
  // Prefer full chromium over headless_shell for accurate font/emoji rendering.
  candidates.sort((a, b) => (a.includes('headless_shell') ? 1 : 0) - (b.includes('headless_shell') ? 1 : 0));
  return candidates[0];
}

export async function getBrowser(): Promise<Browser> {
  if (!browserPromise) {
    const executablePath = findChromeExecutable();
    browserPromise = chromium.launch({
      executablePath,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    });
  }
  return browserPromise;
}

export async function closeBrowser(): Promise<void> {
  if (browserPromise) {
    const b = await browserPromise;
    await b.close();
    browserPromise = null;
  }
}
