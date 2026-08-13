/**
 * Relationship Fingerprint — a signature generative artwork unique to each
 * couple. The same conversation always yields the same image (deterministic
 * seed derived from real signals), so it functions like a visual DNA barcode.
 */
import type { Statistics } from '../stats/statistics.js';

export interface FingerprintSignals {
  seed: string;
  signals: Record<string, number>; // all normalized 0..1
}

function mulberry32(seedNum: number) {
  let a = seedNum >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seedToNumber(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Derive normalized signals + a stable seed from the deterministic statistics. */
export function buildFingerprintSignals(stats: Statistics): FingerprintSignals {
  const total = Math.max(1, stats.totalMessages);
  const hourPeak = Math.max(...stats.messagesByHour, 1);
  const dayPeak = Math.max(...stats.messagesByWeekday, 1);
  const senderRatio = stats.perPerson.length
    ? stats.perPerson[0].percentage / 100
    : 0.5;

  const signals: Record<string, number> = {
    lateNight: clamp(stats.lateNightMessages / total),
    senderBalance: 1 - Math.abs(senderRatio - 0.5) * 2,
    emojiDensity: clamp(
      stats.topEmojis.reduce((s, e) => s + e.count, 0) / total,
    ),
    questionRate: clamp(stats.questionsAsked / total),
    duration: clamp(stats.durationDays / 1825), // 5 years -> 1.0
    hourSpread: entropy(stats.messagesByHour),
    daySpread: entropy(stats.messagesByWeekday),
    peakHour: stats.mostActiveHour / 23,
    hourPeakShare: clamp(hourPeak / total),
    dayPeakShare: clamp(dayPeak / total),
    volume: clamp(Math.log10(total) / 6), // ~1M messages -> 1.0
  };

  const seed = [
    stats.totalMessages,
    stats.mostActiveHour,
    Math.round(senderRatio * 100),
    stats.durationDays,
    stats.topEmojis[0]?.emoji ?? '',
    Math.round(signals.hourSpread * 1000),
  ].join(':');

  return { seed, signals };
}

function clamp(x: number): number {
  return Math.max(0, Math.min(1, x));
}

/** Shannon entropy of a distribution, normalized to 0..1. */
function entropy(arr: number[]): number {
  const sum = arr.reduce((a, b) => a + b, 0);
  if (sum === 0) return 0;
  let h = 0;
  for (const v of arr) {
    if (v <= 0) continue;
    const p = v / sum;
    h -= p * Math.log2(p);
  }
  return clamp(h / Math.log2(arr.length));
}

export interface FingerprintTheme {
  bg: string;
  ink: string;
  accents: string[];
}

export const FINGERPRINT_THEMES: Record<'light' | 'dark', FingerprintTheme> = {
  light: { bg: '#F7F4EF', ink: '#1A1A1A', accents: ['#E4572E', '#F3A712', '#2E86AB', '#8A4FFF'] },
  dark: { bg: '#0E0E12', ink: '#F5F5F0', accents: ['#FF6B4A', '#FFC857', '#57C4E5', '#B18CFF'] },
};

/**
 * Render the fingerprint as a standalone SVG string. The composition is a
 * radial "conversation bloom": concentric rings of marks whose count, angle and
 * size are driven by the normalized signals through the seeded RNG.
 */
export function renderFingerprintSVG(
  fp: FingerprintSignals,
  opts: { size?: number; theme?: 'light' | 'dark'; title?: string } = {},
): string {
  const size = opts.size ?? 1000;
  const theme = FINGERPRINT_THEMES[opts.theme ?? 'light'];
  const rnd = mulberry32(seedToNumber(fp.seed));
  const cx = size / 2;
  const cy = size / 2;
  const s = fp.signals;

  const rings = 5 + Math.round(s.duration * 7); // 5..12 rings
  const maxR = size * 0.42;
  const parts: string[] = [];

  parts.push(`<rect width="${size}" height="${size}" fill="${theme.bg}"/>`);

  // Concentric conversation rings.
  for (let ring = 0; ring < rings; ring++) {
    const t = (ring + 1) / rings;
    const radius = maxR * t;
    const marks = Math.round(12 + s.volume * 60 * t + s.hourSpread * 40);
    const accent = theme.accents[ring % theme.accents.length];
    const jitter = 0.15 + s.lateNight * 0.6;
    for (let i = 0; i < marks; i++) {
      const baseAngle = (i / marks) * Math.PI * 2;
      const a = baseAngle + (rnd() - 0.5) * jitter;
      const rr = radius * (1 + (rnd() - 0.5) * 0.06);
      const x = cx + Math.cos(a) * rr;
      const y = cy + Math.sin(a) * rr;
      const size2 = 1.5 + rnd() * (2 + s.emojiDensity * 8);
      const opacity = (0.25 + rnd() * 0.65).toFixed(2);
      if (rnd() < 0.5 + s.senderBalance * 0.3) {
        parts.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${size2.toFixed(1)}" fill="${accent}" opacity="${opacity}"/>`);
      } else {
        const len = 4 + rnd() * (6 + s.questionRate * 20);
        const x2 = cx + Math.cos(a) * (rr + len);
        const y2 = cy + Math.sin(a) * (rr + len);
        parts.push(`<line x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${accent}" stroke-width="${(0.8 + s.emojiDensity * 2).toFixed(1)}" opacity="${opacity}"/>`);
      }
    }
  }

  // Central core sized by peak-hour concentration.
  const coreR = size * (0.03 + s.hourPeakShare * 0.06);
  parts.push(`<circle cx="${cx}" cy="${cy}" r="${coreR.toFixed(1)}" fill="none" stroke="${theme.ink}" stroke-width="2" opacity="0.85"/>`);
  parts.push(`<circle cx="${cx}" cy="${cy}" r="${(coreR * 0.45).toFixed(1)}" fill="${theme.accents[0]}"/>`);

  const label = opts.title
    ? `<text x="${cx}" y="${size - 40}" text-anchor="middle" font-family="Georgia, serif" font-size="${size * 0.024}" fill="${theme.ink}" opacity="0.6" letter-spacing="4">${escapeXml(opts.title.toUpperCase())}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${parts.join('')}${label}</svg>`;
}

function escapeXml(s: string): string {
  return s.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[c]!);
}
