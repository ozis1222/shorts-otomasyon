/**
 * Privacy-first content filtering.
 *
 * In SAFE mode (the default) messages carrying sensitive categories — sexual
 * content, financial details, addresses, phone numbers, national IDs, health
 * info — are excluded from anything that reaches the final product or the LLM.
 * The raw chat itself is never logged and is deleted per RAW_DATA_RETENTION_DAYS
 * by the pipeline; this module governs what may appear in the deliverable.
 */
import type { ParsedMessage } from '../parser/types.js';
import type { ContentSensitivity } from '../config/index.js';

const PATTERNS: { category: string; re: RegExp }[] = [
  // Contact / identity
  { category: 'phone', re: /(?:\+?\d[\s\-().]?){9,}\d/ },
  { category: 'email', re: /[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}/i },
  { category: 'national_id', re: /\b\d{11}\b|\bTC\s?\d{9,}\b/i },
  { category: 'credit_card', re: /\b(?:\d[ -]?){13,16}\b/ },
  { category: 'iban', re: /\bTR\d{2}[\s\d]{20,}\b|\b[A-Z]{2}\d{2}[A-Z0-9]{10,}\b/ },
  // Address hints
  { category: 'address', re: /\b(sokak|sk\.|cadde|cad\.|mahalle|mah\.|apt|daire|street|avenue|zip code|postal code)\b/i },
  // Financial
  { category: 'financial', re: /\b(password|şifre|pin|salary|maaş|bank account|hesap numarası)\b/i },
  // Health
  { category: 'health', re: /\b(diagnos|depress|anxiety|medication|hastalık|teşhis|ilaç|terapi|therapy|hospital|hastane)\b/i },
  // Sexual / explicit (kept intentionally conservative)
  { category: 'sexual', re: /\b(sex|nude|naked|çıplak|seks)\b/i },
];

export interface RedactionResult {
  safe: boolean;
  categories: string[];
}

export function screenMessage(msg: ParsedMessage): RedactionResult {
  if (msg.type !== 'text') return { safe: true, categories: [] };
  const hits: string[] = [];
  for (const { category, re } of PATTERNS) {
    if (re.test(msg.message)) hits.push(category);
  }
  return { safe: hits.length === 0, categories: hits };
}

/**
 * Returns the subset of messages permitted to surface in the deliverable /
 * be shown to the LLM for quote selection, given the sensitivity level.
 */
export function filterForOutput(
  messages: ParsedMessage[],
  sensitivity: ContentSensitivity,
): ParsedMessage[] {
  if (sensitivity === 'NORMAL') return messages.filter((m) => m.type === 'text');
  return messages.filter((m) => m.type === 'text' && screenMessage(m).safe);
}

/** True if any text in the string trips a sensitive pattern. Used by validators. */
export function containsSensitive(text: string): boolean {
  return PATTERNS.some(({ re }) => re.test(text));
}
