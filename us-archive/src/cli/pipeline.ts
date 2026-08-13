/** CLI: run the pipeline over a real WhatsApp export file. */
import { readFile, mkdir } from 'node:fs/promises';
import { join, basename } from 'node:path';
import { runPipeline } from '../pipeline/orchestrator.js';
import { CoupleSchema } from '../profile/schema.js';

async function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).map((a) => {
      const [k, v] = a.replace(/^--/, '').split('=');
      return [k, v ?? 'true'];
    }),
  );
  const file = args.file || process.argv[2];
  if (!file || file.startsWith('--')) {
    console.error('Usage: npm run run:pipeline -- --file=chat.txt --a="Alex" --b="Mia" [--package=full] [--theme=light]');
    process.exit(1);
  }
  const raw = await readFile(file, 'utf8');
  const orderId = args.order || basename(file).replace(/\.[^.]+$/, '');
  const workDir = join('output', orderId);
  await mkdir(workDir, { recursive: true });

  const couple = CoupleSchema.parse({
    partnerA: args.a || 'Partner 1',
    partnerB: args.b || 'Partner 2',
    tone: args.tone || 'balanced',
    language: args.lang || 'en',
    relationshipStartDate: args.start || null,
  });

  const result = await runPipeline(
    { orderId, workDir, rawChat: raw, couple, packageId: args.package || 'full', theme: (args.theme as any) || 'light', force: args.force === 'true' },
    (e, d) => console.log(e, d ? JSON.stringify(d) : ''),
  );
  console.log('\nDone. PDF:', result.pdfPath, '\nZIP:', result.zipPath);
  process.exit(0);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
