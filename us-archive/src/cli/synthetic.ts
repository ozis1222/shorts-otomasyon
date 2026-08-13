/** CLI: emit a synthetic WhatsApp export to stdout or a file. */
import { writeFile } from 'node:fs/promises';
import { generateSyntheticChat } from '../synthetic/generator.js';

async function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).map((a) => {
      const [k, v] = a.replace(/^--/, '').split('=');
      return [k, v ?? 'true'];
    }),
  );
  const raw = generateSyntheticChat({
    partnerA: args.a || 'Alex',
    partnerB: args.b || 'Mia',
    months: args.months ? Number(args.months) : 36,
    targetMessages: args.messages ? Number(args.messages) : 25000,
    seed: args.seed ? Number(args.seed) : 42,
  });
  if (args.out) {
    await writeFile(args.out, raw);
    console.error(`Wrote ${raw.split('\n').length} lines to ${args.out}`);
  } else {
    process.stdout.write(raw);
  }
}
main();
