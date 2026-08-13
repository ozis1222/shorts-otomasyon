/** Small deterministic text helpers used by the parser and statistics. */

// Matches most emoji: emoji presentation, symbols, dingbats, regional
// indicators, skin-tone / ZWJ sequences. Good enough for counting, not for
// rendering. Uses Unicode property escapes (Node 20+).
const EMOJI_REGEX =
  /(\p{Extended_Pictographic}(️|\p{Emoji_Modifier})?(‍\p{Extended_Pictographic}(️|\p{Emoji_Modifier})?)*|\p{Regional_Indicator}{2})/gu;

const URL_REGEX = /\bhttps?:\/\/[^\s<>()]+|(\bwww\.[^\s<>()]+)/gi;

export function extractEmoji(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(EMOJI_REGEX)) {
    // Skip bare digits/keycaps that Extended_Pictographic sometimes over-matches.
    out.push(m[0]);
  }
  return out;
}

export function extractLinks(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(URL_REGEX)) out.push(m[0]);
  return out;
}

/** Whitespace-based word count. Emoji-only tokens are not counted as words. */
export function countWords(text: string): number {
  const stripped = text.replace(EMOJI_REGEX, ' ').trim();
  if (!stripped) return 0;
  return stripped.split(/\s+/).filter(Boolean).length;
}

/** Lowercased word tokens with punctuation trimmed, for frequency analysis. */
export function tokenize(text: string): string[] {
  const stripped = text.replace(EMOJI_REGEX, ' ').replace(URL_REGEX, ' ');
  return stripped
    .toLowerCase()
    .split(/[\s.,!?;:"'`~()\[\]{}<>/\\|@#$%^&*+=—–…]+/u)
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
}

export function isQuestion(text: string): boolean {
  return /\?\s*$/.test(text.trim()) || /\?/.test(text);
}
