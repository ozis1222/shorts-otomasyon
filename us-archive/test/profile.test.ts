import { describe, it, expect } from 'vitest';
import { generateSyntheticChat } from '../src/synthetic/generator.js';
import { parseWhatsApp } from '../src/parser/whatsapp.js';
import { computeStatistics } from '../src/stats/statistics.js';
import { analyze } from '../src/pipeline/analyze.js';
import { createProvider } from '../src/ai/provider.js';
import { CoupleSchema, RelationshipProfileSchema } from '../src/profile/schema.js';
import { buildMagazineHTML } from '../src/render/magazine.js';
import { validateHTML } from '../src/render/validate.js';
import { buildFingerprintSignals, renderFingerprintSVG } from '../src/fingerprint/fingerprint.js';

describe('profile + rendering (mock provider)', () => {
  it('produces a schema-valid profile and clean HTML end-to-end', async () => {
    const raw = generateSyntheticChat({ months: 6, targetMessages: 2000, seed: 7 });
    const parsed = parseWhatsApp(raw);
    const stats = computeStatistics(parsed.messages);
    const couple = CoupleSchema.parse({ partnerA: 'Alex', partnerB: 'Mia', tone: 'balanced' });
    const profile = await analyze(parsed.messages, stats, couple, 'full', createProvider());

    // Schema is satisfied.
    expect(() => RelationshipProfileSchema.parse(profile)).not.toThrow();

    // DNA scores are bounded.
    for (const d of profile.relationshipDna.dimensions) {
      expect(d.score).toBeGreaterThanOrEqual(0);
      expect(d.score).toBeLessThanOrEqual(100);
    }
    // Archetype percentages sum to 100.
    const sumA = profile.relationshipDna.archetypes.partnerA.reduce((s, a) => s + a.percentage, 0);
    expect(sumA === 0 || sumA === 100).toBe(true);

    // Quotes stay traceable to a message id.
    for (const q of profile.quotes) expect(typeof q.messageId).toBe('number');

    // HTML renders and passes output validation (no undefined/null/placeholder).
    const html = buildMagazineHTML(profile, { theme: 'light' });
    expect(() => validateHTML(html)).not.toThrow();
    expect(html).toContain('Alex');
  });

  it('fingerprint is deterministic for the same stats', () => {
    const raw = generateSyntheticChat({ months: 4, targetMessages: 1500, seed: 3 });
    const stats = computeStatistics(parseWhatsApp(raw).messages);
    const a = buildFingerprintSignals(stats);
    const b = buildFingerprintSignals(stats);
    expect(a.seed).toBe(b.seed);
    expect(renderFingerprintSVG(a, { size: 400 })).toBe(renderFingerprintSVG(b, { size: 400 }));
  });
});
