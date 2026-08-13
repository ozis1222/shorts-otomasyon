/** Render the magazine HTML to a print-ready A4 PDF via headless Chromium. */
import { writeFile } from 'node:fs/promises';
import type { RelationshipProfile } from '../profile/schema.js';
import { buildMagazineHTML, type MagazineOptions } from './magazine.js';
import { validateHTML } from './validate.js';
import { getBrowser } from './browser.js';

export async function renderPDF(
  profile: RelationshipProfile,
  outPath: string,
  opts: MagazineOptions = {},
): Promise<{ path: string; bytes: number }> {
  const html = buildMagazineHTML(profile, opts);
  validateHTML(html); // fail loudly before we ship anything broken

  const browser = await getBrowser();
  const page = await browser.newPage();
  try {
    await page.setContent(html, { waitUntil: 'networkidle' });
    const pdf = await page.pdf({
      width: '210mm',
      height: '297mm',
      printBackground: true,
      preferCSSPageSize: true,
    });
    await writeFile(outPath, pdf);
    return { path: outPath, bytes: pdf.length };
  } finally {
    await page.close();
  }
}
