/**
 * End-to-end demo (spec §51). Generates the synthetic Alex + Mia couple, runs
 * the full pipeline, and writes a real PDF, fingerprint, social cards,
 * wallpapers and a delivery ZIP to ./output/demo.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { generateSyntheticChat } from '../synthetic/generator.js';
import { runPipeline } from '../pipeline/orchestrator.js';
import { CoupleSchema } from '../profile/schema.js';
import { num } from '../render/format.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');

function log(event: string, data?: Record<string, unknown>) {
  const time = new Date().toISOString().slice(11, 19);
  console.log(`  [${time}] ${event}${data ? ' ' + JSON.stringify(data) : ''}`);
}

async function main() {
  const packageId = process.argv[2] || 'full';
  const theme = (process.argv[3] as 'light' | 'dark') || 'light';
  const orderId = 'DEMO-ALEX-MIA';
  const workDir = join(ROOT, 'output', 'demo');
  await mkdir(workDir, { recursive: true });

  console.log('\n╭─ THE US ARCHIVE — end-to-end demo');
  console.log(`│  couple: Alex & Mia · package: ${packageId} · theme: ${theme}\n`);

  console.log('▸ Generating synthetic 3-year chat…');
  const raw = generateSyntheticChat({
    partnerA: 'Alex',
    partnerB: 'Mia',
    startDate: new Date(2022, 5, 1),
    months: 36,
    targetMessages: 25000,
    seed: 42,
  });
  await writeFile(join(workDir, 'raw-chat.txt'), raw);
  log('synthetic.saved', { lines: raw.split('\n').length });

  const couple = CoupleSchema.parse({
    partnerA: 'Alex',
    partnerB: 'Mia',
    relationshipStartDate: '2022-06-15',
    firstDate: '2022-06-20',
    firstTrip: '2022-09-10',
    anniversaryDate: '2023-06-15',
    currentCity: 'Istanbul',
    language: 'en',
    tone: 'balanced',
  });

  console.log('\n▸ Running pipeline…');
  const result = await runPipeline({ orderId, workDir, rawChat: raw, couple, packageId, theme, force: true }, log);

  const s = result.statistics;
  console.log('\n╭─ RESULT');
  console.log(`│  parser: ${result.parserMeta.parsedMessages} messages, order ${result.parserMeta.dateOrder}, format ${result.parserMeta.detectedFormat}`);
  console.log(`│  total messages: ${num(s.totalMessages)}  ·  words: ${num(s.totalWords)}  ·  days: ${num(s.durationDays)}`);
  console.log(`│  split: ${s.perPerson.map((p) => `${p.name} ${p.percentage}%`).join('  ')}`);
  console.log(`│  top emoji: ${s.topEmojis.slice(0, 5).map((e) => e.emoji).join(' ')}`);
  console.log(`│  inside jokes: ${result.profile.insideJokes.length}  ·  eras: ${result.profile.relationshipEras.length}  ·  awards: ${result.profile.awards.length}`);
  console.log(`│  DNA top: ${[...result.profile.relationshipDna.dimensions].sort((a, b) => b.score - a.score).slice(0, 3).map((d) => `${d.name} ${d.score}`).join(', ')}`);
  console.log('│');
  console.log(`│  PDF:   ${result.pdfPath}`);
  console.log(`│  ZIP:   ${result.zipPath}`);
  console.log(`│  assets: ${result.assetCount} files`);
  console.log('╰─ done ✓\n');
  process.exit(0);
}

main().catch((err) => {
  console.error('\n✗ Demo failed:', err);
  process.exit(1);
});
