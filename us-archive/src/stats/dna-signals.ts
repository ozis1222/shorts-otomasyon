/**
 * Deterministic Relationship-DNA signals.
 *
 * SCORING METHOD (documented per spec §7):
 *   1. For each DNA dimension we maintain a small keyword/emoji lexicon plus a
 *      structural signal (e.g. Late Night Energy uses the real share of 00–05h
 *      messages; Chaos uses double-text and burst rates).
 *   2. We count per-message hits, normalize by message volume to a raw rate,
 *      then map the rate through a saturating curve `100 * (1 - e^(-k*rate))`
 *      so a handful of hits doesn't peg the score at 100.
 *   3. The LLM stage may nudge each score by at most ±15 (see ai/pipeline), so
 *      the number is always anchored to real signal, never invented.
 *
 * Archetypes are scored the same way per person, then the top ≤3 are normalized
 * to sum to 100 for display.
 */
import type { ParsedMessage } from '../parser/types.js';
import type { Statistics } from './statistics.js';
import { tokenize } from '../util/text.js';

type Lexicon = { words: string[]; emoji: string[] };

const DNA_LEXICONS: Record<string, Lexicon> = {
  Affection: {
    words: ['love', 'miss', 'babe', 'baby', 'darling', 'aşkım', 'seviyorum', 'özledim', 'canım', 'sweetheart', 'cutie'],
    emoji: ['❤️', '😍', '🥰', '😘', '💕', '💗', '💞', '❤', '♥️'],
  },
  Humor: {
    words: ['lol', 'lmao', 'haha', 'hahaha', 'joke', 'funny', 'komik', 'aha', 'ahaha', 'rofl'],
    emoji: ['😂', '🤣', '😆', '😅', '😹'],
  },
  'Deep Talks': {
    words: ['think', 'feel', 'life', 'future', 'meaning', 'believe', 'dream', 'hayat', 'düşünüyorum', 'hissediyorum', 'gelecek', 'anlam'],
    emoji: ['🤔', '💭'],
  },
  Flirting: {
    words: ['cute', 'hot', 'sexy', 'kiss', 'öpücük', 'tatlı', 'yakışıklı', 'güzel', 'gorgeous', 'wink'],
    emoji: ['😏', '😉', '😜', '👀', '🔥', '😈'],
  },
  Chaos: {
    words: ['omg', 'wtf', 'aaaa', 'chaos', 'panic', 'aaa', 'yaaa', 'noo', 'stop', 'random'],
    emoji: ['😱', '🙈', '💀', '😭', '🤯'],
  },
  Support: {
    words: ['ok', 'okay', 'here', 'sorry', 'proud', 'got you', 'help', 'destek', 'buradayım', 'üzülme', 'geçmiş olsun', 'thank'],
    emoji: ['🫂', '🙏', '💪', '🤗'],
  },
  Planning: {
    words: ['tomorrow', 'plan', 'meet', 'when', 'time', 'book', 'reservation', 'yarın', 'plan', 'buluşalım', 'saat', 'randevu'],
    emoji: ['📅', '⏰', '📍'],
  },
  'Late Night Energy': { words: [], emoji: ['🌙', '🌛', '😴'] }, // structural, see below
};

function saturate(rate: number, k: number): number {
  return Math.round(100 * (1 - Math.exp(-k * rate)));
}

function countHits(msgs: ParsedMessage[], lex: Lexicon): number {
  let hits = 0;
  for (const m of msgs) {
    if (m.type === 'text') {
      const toks = new Set(tokenize(m.message));
      for (const w of lex.words) if (toks.has(w)) hits++;
    }
    for (const e of m.emoji) if (lex.emoji.includes(e)) hits++;
  }
  return hits;
}

export function computeDnaSignals(
  msgs: ParsedMessage[],
  stats: Statistics,
): { name: string; score: number }[] {
  const textMsgs = msgs.filter((m) => m.type === 'text');
  const n = Math.max(1, textMsgs.length);
  const out: { name: string; score: number }[] = [];

  for (const [name, lex] of Object.entries(DNA_LEXICONS)) {
    if (name === 'Late Night Energy') {
      const rate = stats.lateNightMessages / Math.max(1, stats.totalMessages);
      out.push({ name, score: Math.min(100, saturate(rate, 12)) });
      continue;
    }
    if (name === 'Chaos') {
      const doubleTexts = stats.perPerson.reduce((s, p) => s + p.doubleTexts, 0);
      const rate = (countHits(textMsgs, lex) + doubleTexts * 0.5) / n;
      out.push({ name, score: Math.min(100, saturate(rate, 6)) });
      continue;
    }
    const rate = countHits(textMsgs, lex) / n;
    out.push({ name, score: Math.min(100, Math.max(3, saturate(rate, 8))) });
  }
  return out;
}

// ---- Archetypes -------------------------------------------------------------

const ARCHETYPE_LEXICONS: Record<string, Lexicon> = {
  'The Protector': { words: ['careful', 'safe', 'worried', 'okay', 'dikkat', 'merak', 'iyi misin'], emoji: ['🫂', '🙏'] },
  'The Comedian': { words: ['lol', 'lmao', 'haha', 'joke', 'komik'], emoji: ['😂', '🤣', '😆'] },
  'The Planner': { words: ['plan', 'tomorrow', 'schedule', 'meet', 'yarın', 'saat', 'buluşalım'], emoji: ['📅', '⏰'] },
  'The Storyteller': { words: ['then', 'so', 'suddenly', 'because', 'sonra', 'çünkü', 'birden'], emoji: [] },
  'The Problem Solver': { words: ['fix', 'solution', 'try', 'maybe', 'çözüm', 'dene', 'belki'], emoji: ['🛠️', '💡'] },
  'The Chaos Agent': { words: ['omg', 'random', 'wtf', 'aaaa'], emoji: ['💀', '🙈', '🤯'] },
  'The Romantic': { words: ['love', 'miss', 'aşkım', 'özledim', 'canım'], emoji: ['❤️', '🥰', '😘'] },
  'The Late-Night Philosopher': { words: ['think', 'life', 'meaning', 'universe', 'hayat', 'anlam'], emoji: ['🌙', '💭'] },
};

export function computeArchetypes(
  msgs: ParsedMessage[],
  person: string,
): { name: string; percentage: number }[] {
  const own = msgs.filter((m) => m.sender === person);
  const scored = Object.entries(ARCHETYPE_LEXICONS).map(([name, lex]) => ({
    name,
    raw: countHits(own, lex) + 0.001, // tiny epsilon so ties resolve deterministically
  }));
  scored.sort((a, b) => b.raw - a.raw);
  const top = scored.slice(0, 3);
  const sum = top.reduce((s, a) => s + a.raw, 0) || 1;
  const pct = top.map((a) => ({ name: a.name, percentage: Math.round((a.raw / sum) * 100) }));
  // Fix rounding so percentages sum to exactly 100.
  const diff = 100 - pct.reduce((s, p) => s + p.percentage, 0);
  if (pct.length) pct[0].percentage += diff;
  return pct;
}
