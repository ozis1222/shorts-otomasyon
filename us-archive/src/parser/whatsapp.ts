/**
 * Robust WhatsApp .txt export parser.
 *
 * Handles the many export dialects WhatsApp produces:
 *  - 12h and 24h clocks, with/without seconds, AM/PM (incl. narrow no-break space)
 *  - bracketed `[dd/mm/yy, hh:mm:ss]` and dashed `dd/mm/yyyy, hh:mm -` layouts
 *  - DMY vs MDY date order (auto-detected from the data)
 *  - multiline messages, emoji, URLs, Turkish/Unicode text
 *  - media/sticker/gif/voice/deleted placeholders in several UI languages
 *  - system lines (encryption notice, "X added Y", name changes…)
 *
 * The parser is fully deterministic — no network, no LLM.
 */
import type { MessageType, ParseResult, ParsedMessage } from './types.js';
import { countWords, extractEmoji, extractLinks } from '../util/text.js';

// A "header" is the start-of-message prefix up to and including the sender colon.
// Two broad layouts, both tolerant of the narrow-no-break-space WhatsApp uses.
const SP = '[\\u00a0\\u202f ]'; // ordinary / no-break / narrow-no-break space
const TIME = `\\d{1,2}[:.]\\d{2}(?:[:.]\\d{2})?(?:${SP}?[APap][.]?${SP}?[Mm][.]?)?`;
const DATE = `\\d{1,4}[\\/.\\-]\\d{1,2}[\\/.\\-]\\d{1,4}`;

// [12/03/2023, 21:45:07] Name: message
const BRACKET_RE = new RegExp(
  `^\\[(${DATE}),?${SP}?(${TIME})\\]${SP}?([^:]+?):${SP}?([\\s\\S]*)$`,
);
// 12/03/2023, 21:45 - Name: message   (system lines have no "Name:")
const DASH_RE = new RegExp(
  `^(${DATE}),?${SP}?(${TIME})${SP}?[-–]${SP}?([\\s\\S]*)$`,
);

interface RawHeader {
  date: string;
  time: string;
  /** Everything after the timestamp separator. */
  rest: string;
}

function matchHeader(line: string): RawHeader | null {
  const b = BRACKET_RE.exec(line);
  if (b) return { date: b[1], time: b[2], rest: `${b[3]}: ${b[4]}` };
  const d = DASH_RE.exec(line);
  if (d) return { date: d[1], time: d[2], rest: d[3] };
  return null;
}

/** Split "Name: body" — but only when the colon really is a sender separator. */
function splitSender(rest: string): { sender: string | null; body: string } {
  const idx = rest.indexOf(': ');
  if (idx === -1) {
    // Could be "Name:" with an empty body, or a system line.
    const bare = rest.match(/^([^:]{1,60}):$/);
    if (bare) return { sender: bare[1].trim(), body: '' };
    return { sender: null, body: rest };
  }
  const sender = rest.slice(0, idx);
  // Senders never contain newlines; if they do, this is a system line.
  if (sender.includes('\n') || sender.length > 60) return { sender: null, body: rest };
  return { sender: sender.trim(), body: rest.slice(idx + 2) };
}

// Media / placeholder detection across common WhatsApp UI languages (EN + TR).
const MEDIA_PATTERNS: [RegExp, MessageType][] = [
  [/\bsticker omitted\b|\bçıkartma dahil edilmedi\b|\bçıkartma atlandı\b/i, 'sticker'],
  [/\bGIF omitted\b|\bGIF dahil edilmedi\b/i, 'gif'],
  [/\bimage omitted\b|\bfotoğraf dahil edilmedi\b|\bgörüntü dahil edilmedi\b|\bresim dahil edilmedi\b/i, 'image'],
  [/\bvideo omitted\b|\bvideo dahil edilmedi\b/i, 'video'],
  [/\baudio omitted\b|\bses dahil edilmedi\b/i, 'audio'],
  [/\bvoice message\b|\bses kaydı\b|\bPTT-\d/i, 'voice'],
  [/\bdocument omitted\b|\bbelge dahil edilmedi\b/i, 'document'],
  [/\bContact card omitted\b|\bkişi kartı\b/i, 'contact'],
  [/<Media omitted>|\bmedya dahil edilmedi\b|<attached:/i, 'media'],
  [/\blocation:\s*https?:/i, 'location'],
];

const DELETED_PATTERNS =
  /\bThis message was deleted\b|\bYou deleted this message\b|\bBu mesaj silindi\b|\bBu mesajı sildiniz\b/i;

// Heuristics for lines that are system notices, not messages from a person.
const SYSTEM_PATTERNS = [
  /end-to-end encrypted/i,
  /uçtan uca şifreli/i,
  /Messages and calls are/i,
  /created group|grubu oluşturdu/i,
  /added you|seni ekledi|added |ekledi/i,
  /left$|ayrıldı$/i,
  /changed the subject|konuyu değiştirdi/i,
  /changed this group's icon|grup simgesini değiştirdi/i,
  /changed their phone number|telefon numarasını değiştirdi/i,
  /security code changed|güvenlik kodu değişti/i,
  /You're now an admin|artık yönetici/i,
];

function classify(body: string): MessageType {
  if (DELETED_PATTERNS.test(body)) return 'deleted';
  for (const [re, type] of MEDIA_PATTERNS) if (re.test(body)) return type;
  return 'text';
}

function looksSystem(rest: string): boolean {
  return SYSTEM_PATTERNS.some((re) => re.test(rest));
}

// ---- date parsing -----------------------------------------------------------

interface DateGuess {
  a: number;
  b: number;
  y: number;
}

function parseDateParts(date: string): DateGuess | null {
  const m = date.split(/[\/.\-]/).map((x) => parseInt(x, 10));
  if (m.length !== 3 || m.some((n) => Number.isNaN(n))) return null;
  let [a, b, y] = m;
  // Normalize a YMD layout (first field is the 4-digit year).
  if (String(m[0]).length === 4) {
    return { y: m[0], a: m[1], b: m[2] };
  }
  if (y < 100) y += y < 70 ? 2000 : 1900;
  return { a, b, y };
}

/** Decide DMY vs MDY by scanning: if any first-field > 12 it must be a day. */
function detectDateOrder(dates: string[]): 'DMY' | 'MDY' | 'YMD' {
  let firstOver12 = false;
  let secondOver12 = false;
  let ymd = false;
  for (const d of dates) {
    const parts = d.split(/[\/.\-]/);
    if (parts[0]?.length === 4) {
      ymd = true;
      continue;
    }
    const a = parseInt(parts[0], 10);
    const b = parseInt(parts[1], 10);
    if (a > 12) firstOver12 = true;
    if (b > 12) secondOver12 = true;
  }
  if (ymd && !firstOver12 && !secondOver12) return 'YMD';
  if (firstOver12 && !secondOver12) return 'DMY';
  if (secondOver12 && !firstOver12) return 'MDY';
  return 'DMY'; // WhatsApp's global default; ambiguous data falls back to this.
}

function parseTime(time: string): { h: number; min: number; s: number } {
  const isPM = /p[.]?\s?m/i.test(time);
  const isAM = /a[.]?\s?m/i.test(time);
  const nums = time.replace(/[^\d:.]/g, '').split(/[:.]/).map((x) => parseInt(x, 10));
  let h = nums[0] || 0;
  const min = nums[1] || 0;
  const s = nums[2] || 0;
  if (isPM && h < 12) h += 12;
  if (isAM && h === 12) h = 0;
  return { h, min, s };
}

function toDate(date: string, time: string, order: 'DMY' | 'MDY' | 'YMD'): Date | null {
  const dp = parseDateParts(date);
  if (!dp) return null;
  const { h, min, s } = parseTime(time);
  let day: number, month: number;
  if (order === 'YMD') {
    day = dp.b;
    month = dp.a;
  } else if (order === 'MDY') {
    month = dp.a;
    day = dp.b;
  } else {
    day = dp.a;
    month = dp.b;
  }
  const d = new Date(dp.y, month - 1, day, h, min, s);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

// ---- main -------------------------------------------------------------------

export function parseWhatsApp(raw: string): ParseResult {
  // Strip UTF-8 BOM and normalize line endings; keep Unicode intact.
  const text = raw.replace(/^﻿/, '').replace(/\r\n?/g, '\n');
  const lines = text.split('\n');

  // First pass: collect header dates to detect ordering + primary layout.
  const headerDates: string[] = [];
  let bracketCount = 0;
  let dashCount = 0;
  for (const line of lines) {
    const h = matchHeader(line);
    if (h) {
      headerDates.push(h.date);
      if (line.startsWith('[')) bracketCount++;
      else dashCount++;
    }
  }
  const dateOrder = headerDates.length ? detectDateOrder(headerDates) : 'unknown';
  const detectedFormat =
    bracketCount > dashCount ? 'bracketed' : dashCount > 0 ? 'dashed' : 'unknown';

  const messages: ParsedMessage[] = [];
  const participants = new Set<string>();
  let systemMessages = 0;
  let unparsedLines = 0;
  let id = 0;
  let current: { date: string; time: string; sender: string | null; body: string } | null = null;

  const flush = () => {
    if (!current) return;
    const order = dateOrder === 'unknown' ? 'DMY' : dateOrder;
    const d = toDate(current.date, current.time, order);
    const body = current.body.replace(/‎/g, '').trimEnd();
    if (current.sender === null || looksSystem(current.body)) {
      systemMessages++;
      if (d) {
        messages.push({
          id: id++,
          timestamp: d.toISOString(),
          ts: d.getTime(),
          sender: 'System',
          message: body,
          type: 'system',
          links: [],
          emoji: [],
          wordCount: 0,
        });
      }
      current = null;
      return;
    }
    const type = classify(body);
    const isText = type === 'text';
    participants.add(current.sender);
    messages.push({
      id: id++,
      timestamp: d ? d.toISOString() : new Date(0).toISOString(),
      ts: d ? d.getTime() : 0,
      sender: current.sender,
      message: body,
      type,
      links: isText ? extractLinks(body) : [],
      emoji: isText ? extractEmoji(body) : [],
      wordCount: isText ? countWords(body) : 0,
    });
    current = null;
  };

  for (const line of lines) {
    const h = matchHeader(line);
    if (h) {
      flush();
      const { sender, body } = splitSender(h.rest);
      current = { date: h.date, time: h.time, sender, body };
    } else if (current) {
      // Continuation of a multiline message.
      current.body += '\n' + line;
    } else if (line.trim() !== '') {
      unparsedLines++;
    }
  }
  flush();

  const humanTs = messages.filter((m) => m.type !== 'system' && m.ts > 0).map((m) => m.ts);
  const firstTs = humanTs.length ? Math.min(...humanTs) : null;
  const lastTs = humanTs.length ? Math.max(...humanTs) : null;

  return {
    messages,
    participants: [...participants],
    meta: {
      totalLines: lines.length,
      parsedMessages: messages.filter((m) => m.type !== 'system').length,
      systemMessages,
      unparsedLines,
      detectedFormat,
      dateOrder,
      firstTimestamp: firstTs ? new Date(firstTs).toISOString() : null,
      lastTimestamp: lastTs ? new Date(lastTs).toISOString() : null,
    },
  };
}
