/**
 * Deterministic statistics. Everything numeric in the final product is computed
 * here in plain code — the LLM never counts, so numbers can't be hallucinated.
 */
import type { ParsedMessage } from '../parser/types.js';
import { config } from '../config/index.js';
import { isQuestion, tokenize } from '../util/text.js';

export interface PerPerson {
  name: string;
  messages: number;
  percentage: number;
  words: number;
  avgMessageLength: number;
  emojis: number;
  questions: number;
  mediaCount: number;
  voiceCount: number;
  conversationsStarted: number;
  lateNightMessages: number;
  doubleTexts: number;
  longestMessageId: number | null;
}

export interface Statistics {
  totalMessages: number;
  totalWords: number;
  firstMessageDate: string | null;
  lastMessageDate: string | null;
  durationDays: number;
  avgMessagesPerDay: number;
  medianMessageLength: number;
  perPerson: PerPerson[];
  topEmojis: { emoji: string; count: number }[];
  topWords: { word: string; count: number }[];
  topPhrases: { phrase: string; count: number }[];
  messagesByHour: number[]; // length 24
  messagesByWeekday: number[]; // length 7, 0 = Sunday
  messagesByMonth: { month: string; count: number }[];
  mostActiveDay: { date: string; count: number } | null;
  mostActiveMonth: { month: string; count: number } | null;
  mostActiveHour: number;
  lateNightMessages: number; // 00:00–04:59
  earlyMorningMessages: number; // 05:00–07:59
  questionsAsked: number;
  linksShared: number;
  mediaReferences: number;
  voiceReferences: number;
  longestQuietPeriod: { days: number; from: string; to: string } | null;
  longestSessionMessages: number;
  totalSessions: number;
  starterRatio: { name: string; percentage: number }[];
}

const STOPWORDS = new Set(
  (
    'the a an and or but if then to of in on at for with as is are was were be been being ' +
    'i you he she it we they me him her us them my your his its our their this that these those ' +
    'do does did done have has had will would can could should not no yes so just get got go went ' +
    // Turkish
    've bir bu şu o ben sen biz siz için ama de da ki mi mı mu mü çok az ne çünkü gibi ise ' +
    'evet hayır ya yani daha en her hiç şey nasıl neden'
  ).split(/\s+/),
);

function median(nums: number[]): number {
  if (nums.length === 0) return 0;
  const s = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function isLateNight(hour: number): boolean {
  return hour >= 0 && hour < 5;
}

/** Group messages into conversation sessions separated by a gap threshold. */
function computeSessions(msgs: ParsedMessage[]): ParsedMessage[][] {
  const gapMs = config.sessionGapHours * 3600 * 1000;
  const sessions: ParsedMessage[][] = [];
  let cur: ParsedMessage[] = [];
  let last = -Infinity;
  for (const m of msgs) {
    if (m.ts - last > gapMs && cur.length) {
      sessions.push(cur);
      cur = [];
    }
    cur.push(m);
    last = m.ts;
  }
  if (cur.length) sessions.push(cur);
  return sessions;
}

export function computeStatistics(all: ParsedMessage[]): Statistics {
  // Only real, timestamped human messages count toward statistics.
  const msgs = all
    .filter((m) => m.type !== 'system' && m.ts > 0)
    .sort((a, b) => a.ts - b.ts);

  const names = [...new Set(msgs.map((m) => m.sender))];
  const total = msgs.length;
  const totalWords = msgs.reduce((s, m) => s + m.wordCount, 0);

  // Per-person accumulators.
  const per = new Map<string, PerPerson & { lengths: number[] }>();
  for (const n of names) {
    per.set(n, {
      name: n,
      messages: 0,
      percentage: 0,
      words: 0,
      avgMessageLength: 0,
      emojis: 0,
      questions: 0,
      mediaCount: 0,
      voiceCount: 0,
      conversationsStarted: 0,
      lateNightMessages: 0,
      doubleTexts: 0,
      longestMessageId: null,
      lengths: [],
    });
  }

  const byHour = new Array(24).fill(0);
  const byWeekday = new Array(7).fill(0);
  const byMonth = new Map<string, number>();
  const byDay = new Map<string, number>();
  const emojiCounts = new Map<string, number>();
  const wordCounts = new Map<string, number>();
  const bigramCounts = new Map<string, number>();
  const lengths: number[] = [];
  const longestPer = new Map<string, number>(); // name -> max chars

  let lateNight = 0;
  let earlyMorning = 0;
  let questions = 0;
  let links = 0;
  let media = 0;
  let voice = 0;
  let prevSender: string | null = null;

  for (const m of msgs) {
    const p = per.get(m.sender)!;
    p.messages++;
    p.words += m.wordCount;
    p.emojis += m.emoji.length;
    const d = new Date(m.ts);
    const hour = d.getHours();
    byHour[hour]++;
    byWeekday[d.getDay()]++;
    const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    byMonth.set(monthKey, (byMonth.get(monthKey) || 0) + 1);
    const dayKey = d.toISOString().slice(0, 10);
    byDay.set(dayKey, (byDay.get(dayKey) || 0) + 1);

    if (isLateNight(hour)) {
      lateNight++;
      p.lateNightMessages++;
    }
    if (hour >= 5 && hour < 8) earlyMorning++;

    if (m.type === 'text') {
      const len = m.message.length;
      lengths.push(len);
      p.lengths.push(len);
      if (len > (longestPer.get(m.sender) || -1)) {
        longestPer.set(m.sender, len);
        p.longestMessageId = m.id;
      }
      if (isQuestion(m.message)) {
        questions++;
        p.questions++;
      }
      for (const e of m.emoji) emojiCounts.set(e, (emojiCounts.get(e) || 0) + 1);
      links += m.links.length;

      const toks = tokenize(m.message);
      for (const t of toks) {
        if (t.length < 2 || STOPWORDS.has(t) || /^\d+$/.test(t)) continue;
        wordCounts.set(t, (wordCounts.get(t) || 0) + 1);
      }
      const contentToks = toks.filter((t) => t.length >= 2 && !/^\d+$/.test(t));
      for (let i = 0; i < contentToks.length - 1; i++) {
        const bg = `${contentToks[i]} ${contentToks[i + 1]}`;
        bigramCounts.set(bg, (bigramCounts.get(bg) || 0) + 1);
      }
    } else if (m.type === 'voice' || m.type === 'audio') {
      voice++;
      p.voiceCount++;
      p.mediaCount++;
    } else if (['media', 'image', 'video', 'sticker', 'gif', 'document'].includes(m.type)) {
      media++;
      p.mediaCount++;
    }

    // Double text: same sender messages back-to-back.
    if (prevSender === m.sender) p.doubleTexts++;
    prevSender = m.sender;
  }

  // Sessions & who-starts.
  const sessions = computeSessions(msgs);
  const startCounts = new Map<string, number>();
  let longestSession = 0;
  for (const s of sessions) {
    const starter = s[0].sender;
    startCounts.set(starter, (startCounts.get(starter) || 0) + 1);
    if (s.length > longestSession) longestSession = s.length;
  }
  for (const [name, count] of startCounts) {
    const p = per.get(name);
    if (p) p.conversationsStarted = count;
  }

  // Longest quiet period between consecutive messages.
  let longestQuiet: Statistics['longestQuietPeriod'] = null;
  for (let i = 1; i < msgs.length; i++) {
    const gap = msgs[i].ts - msgs[i - 1].ts;
    if (!longestQuiet || gap > longestQuiet.days * 86400000) {
      longestQuiet = {
        days: gap / 86400000,
        from: msgs[i - 1].timestamp,
        to: msgs[i].timestamp,
      };
    }
  }
  if (longestQuiet) longestQuiet.days = Math.round(longestQuiet.days * 10) / 10;

  // Finalize per-person.
  const perPerson: PerPerson[] = [...per.values()].map((p) => {
    const { lengths: pl, ...rest } = p;
    return {
      ...rest,
      percentage: total ? Math.round((p.messages / total) * 1000) / 10 : 0,
      avgMessageLength: pl.length ? Math.round(pl.reduce((a, b) => a + b, 0) / pl.length) : 0,
    };
  });

  const firstTs = msgs.length ? msgs[0].ts : null;
  const lastTs = msgs.length ? msgs[msgs.length - 1].ts : null;
  const durationDays =
    firstTs && lastTs ? Math.max(1, Math.round((lastTs - firstTs) / 86400000)) : 0;

  const sortedDays = [...byDay.entries()].sort((a, b) => b[1] - a[1]);
  const sortedMonths = [...byMonth.entries()].sort((a, b) => b[1] - a[1]);
  const monthsChrono = [...byMonth.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  const starterTotal = [...startCounts.values()].reduce((a, b) => a + b, 0) || 1;
  const starterRatio = [...startCounts.entries()]
    .map(([name, c]) => ({ name, percentage: Math.round((c / starterTotal) * 1000) / 10 }))
    .sort((a, b) => b.percentage - a.percentage);

  return {
    totalMessages: total,
    totalWords,
    firstMessageDate: firstTs ? new Date(firstTs).toISOString() : null,
    lastMessageDate: lastTs ? new Date(lastTs).toISOString() : null,
    durationDays,
    avgMessagesPerDay: durationDays ? Math.round((total / durationDays) * 10) / 10 : 0,
    medianMessageLength: Math.round(median(lengths)),
    perPerson,
    topEmojis: topN(emojiCounts, 10).map(([emoji, count]) => ({ emoji, count })),
    topWords: topN(wordCounts, 15).map(([word, count]) => ({ word, count })),
    topPhrases: topN(bigramCounts, 10)
      .filter(([, c]) => c >= 3)
      .map(([phrase, count]) => ({ phrase, count })),
    messagesByHour: byHour,
    messagesByWeekday: byWeekday,
    messagesByMonth: monthsChrono.map(([month, count]) => ({ month, count })),
    mostActiveDay: sortedDays.length ? { date: sortedDays[0][0], count: sortedDays[0][1] } : null,
    mostActiveMonth: sortedMonths.length
      ? { month: sortedMonths[0][0], count: sortedMonths[0][1] }
      : null,
    mostActiveHour: byHour.indexOf(Math.max(...byHour)),
    lateNightMessages: lateNight,
    earlyMorningMessages: earlyMorning,
    questionsAsked: questions,
    linksShared: links,
    mediaReferences: media,
    voiceReferences: voice,
    longestQuietPeriod: longestQuiet,
    longestSessionMessages: longestSession,
    totalSessions: sessions.length,
    starterRatio,
  };
}

function topN(map: Map<string, number>, n: number): [string, number][] {
  return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}
