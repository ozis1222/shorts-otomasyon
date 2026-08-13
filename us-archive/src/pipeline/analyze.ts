/**
 * AI analysis pipeline (spec §22). Stages:
 *   1. deterministic statistics (already computed upstream)
 *   2. candidate extraction  — inside jokes, eras, awards, moments, who-cards
 *   3. LLM phrasing per stage (mock offline) with Zod-validated output
 *   4. DNA + archetypes (deterministic signals, LLM may nudge)
 *   5. final synthesis (cover copy, future letter…)
 * The result is one canonical RelationshipProfile; the renderer never re-queries
 * the model.
 */
import { config } from '../config/index.js';
import type { ParsedMessage } from '../parser/types.js';
import type { Statistics } from '../stats/statistics.js';
import { computeArchetypes, computeDnaSignals } from '../stats/dna-signals.js';
import { buildFingerprintSignals } from '../fingerprint/fingerprint.js';
import { filterForOutput } from '../privacy/redact.js';
import { tokenize } from '../util/text.js';
import type { ModelProvider } from '../ai/provider.js';
import {
  awardsPrompt,
  communicationPrompt,
  creativePrompt,
  dictionaryPrompt,
  erasPrompt,
  insideJokesPrompt,
  memorablePrompt,
} from '../ai/prompts/index.js';
import {
  RelationshipProfileSchema,
  type Couple,
  type RelationshipProfile,
} from '../profile/schema.js';

// Common words that should never be treated as an inside joke, even if frequent.
const COMMON = new Set(
  'yeah okay good going really thing think know like just want need come back time today tomorrow tonight lol haha love miss home work morning night hahaha tamam evet nasıl güzel bugün yarın'.split(
    /\s+/,
  ),
);

function extractJokeCandidates(msgs: ParsedMessage[], stats: Statistics) {
  const counts = new Map<string, { count: number; ids: number[]; days: Set<string> }>();
  for (const m of msgs) {
    if (m.type !== 'text') continue;
    const day = m.timestamp.slice(0, 10);
    for (const t of new Set(tokenize(m.message))) {
      if (t.length < 3 || COMMON.has(t) || /^\d+$/.test(t)) continue;
      const e = counts.get(t) || { count: 0, ids: [], days: new Set() };
      e.count++;
      if (e.ids.length < 5) e.ids.push(m.id);
      e.days.add(day);
      counts.set(t, e);
    }
  }
  // Inside jokes recur across many days but aren't in the global top-5 (those
  // are just the couple's everyday words). Distinctiveness = recurs on >=3 days.
  const topWords = new Set(stats.topWords.slice(0, 5).map((w) => w.word));
  return [...counts.entries()]
    .filter(([term, e]) => e.count >= 4 && e.days.size >= 3 && !topWords.has(term))
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 12)
    .map(([term, e]) => ({ term, count: e.count, evidenceIds: e.ids }));
}

function bucketEras(msgs: ParsedMessage[], stats: Statistics) {
  const text = msgs.filter((m) => m.type === 'text' && m.ts > 0).sort((a, b) => a.ts - b.ts);
  if (text.length < 10) return [];
  const target = Math.min(6, Math.max(3, Math.round(stats.durationDays / 120)));
  const per = Math.ceil(text.length / target);
  const eras: any[] = [];
  for (let i = 0; i < text.length; i += per) {
    const slice = text.slice(i, i + per);
    const words = new Map<string, number>();
    for (const m of slice)
      for (const t of tokenize(m.message))
        if (t.length >= 4 && !COMMON.has(t)) words.set(t, (words.get(t) || 0) + 1);
    const topWords = [...words.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map((w) => w[0]);
    const start = new Date(slice[0].ts);
    const startDate = slice[0].timestamp;
    const endDate = slice[slice.length - 1].timestamp;
    const month = start.toLocaleString('en-US', { month: 'long' });
    eras.push({
      title: `${month} ${start.getFullYear()}`,
      startDate,
      endDate,
      messageCount: slice.length,
      topWords,
    });
  }
  return eras;
}

function extractAwards(stats: Statistics) {
  const awards: { category: string; winner: string; stat: string }[] = [];
  const byEmoji = [...stats.perPerson].sort((a, b) => b.emojis - a.emojis);
  const byLate = [...stats.perPerson].sort((a, b) => b.lateNightMessages - a.lateNightMessages);
  const byDouble = [...stats.perPerson].sort((a, b) => b.doubleTexts - a.doubleTexts);
  const byQ = [...stats.perPerson].sort((a, b) => b.questions - a.questions);
  const byWords = [...stats.perPerson].sort((a, b) => b.avgMessageLength - a.avgMessageLength);
  const byStart = stats.starterRatio;

  if (byEmoji[0]?.emojis) awards.push({ category: 'Emoji Champion', winner: byEmoji[0].name, stat: `${byEmoji[0].emojis.toLocaleString()} emojis sent.` });
  if (byLate[0]?.lateNightMessages) awards.push({ category: 'Late Night Champion', winner: byLate[0].name, stat: `${byLate[0].lateNightMessages.toLocaleString()} messages after midnight.` });
  if (byDouble[0]?.doubleTexts) awards.push({ category: 'Double Text Champion', winner: byDouble[0].name, stat: `${byDouble[0].doubleTexts.toLocaleString()} back-to-back sends.` });
  if (byQ[0]?.questions) awards.push({ category: 'Most Curious', winner: byQ[0].name, stat: `${byQ[0].questions.toLocaleString()} questions asked.` });
  if (byWords[0]?.avgMessageLength) awards.push({ category: 'Longest Story', winner: byWords[0].name, stat: `${byWords[0].avgMessageLength} characters per message on average.` });
  if (byStart[0]) awards.push({ category: 'Conversation Starter', winner: byStart[0].name, stat: `Started ${byStart[0].percentage}% of your conversations.` });
  awards.push({ category: 'Most Active Day Award', winner: 'Both of you', stat: stats.mostActiveDay ? `${stats.mostActiveDay.count} messages on ${stats.mostActiveDay.date}.` : 'A record-breaking day.' });
  return awards;
}

function extractMemorable(msgs: ParsedMessage[]) {
  // Pick a few short, safe conversation snippets rich in affection/humor emoji.
  const safe = filterForOutput(msgs, config.contentSensitivity);
  const safeIds = new Set(safe.map((m) => m.id));
  const affection = ['❤️', '😂', '🥰', '😍', '🤣', '😭', '😘'];
  const seen = new Set<number>();
  const moments: any[] = [];
  const sorted = msgs.filter((m) => m.ts > 0).sort((a, b) => a.ts - b.ts);
  for (let i = 0; i < sorted.length && moments.length < 4; i++) {
    const m = sorted[i];
    if (!safeIds.has(m.id) || seen.has(m.id)) continue;
    if (!m.emoji.some((e) => affection.includes(e))) continue;
    // Grab a 3-message window (this + neighbors) that are safe & short.
    const window = sorted
      .slice(Math.max(0, i - 1), i + 2)
      .filter((w) => safeIds.has(w.id) && w.message.length <= 140 && w.message.length > 0);
    if (window.length < 2) continue;
    window.forEach((w) => seen.add(w.id));
    moments.push({
      title: 'A small moment',
      description: '',
      quotes: window.map((w) => ({ messageId: w.id, sender: w.sender, text: w.message })),
    });
  }
  return moments;
}

function buildWhoCards(stats: Statistics) {
  const cards: { question: string; winner: string; percentage: number; loserPercentage?: number }[] = [];
  const p = stats.perPerson;
  if (p.length >= 2) {
    const [a, b] = p;
    const texts = a.messages >= b.messages ? a : b;
    cards.push({ question: 'Who texts more?', winner: texts.name, percentage: texts.percentage, loserPercentage: 100 - texts.percentage });
    const emoji = a.emojis >= b.emojis ? a : b;
    const eTot = a.emojis + b.emojis || 1;
    cards.push({ question: 'Who sends more emojis?', winner: emoji.name, percentage: Math.round((emoji.emojis / eTot) * 100) });
    const late = a.lateNightMessages >= b.lateNightMessages ? a : b;
    const lTot = a.lateNightMessages + b.lateNightMessages || 1;
    cards.push({ question: 'Who texts later at night?', winner: late.name, percentage: Math.round((late.lateNightMessages / lTot) * 100) });
    const q = a.questions >= b.questions ? a : b;
    const qTot = a.questions + b.questions || 1;
    cards.push({ question: 'Who asks more questions?', winner: q.name, percentage: Math.round((q.questions / qTot) * 100) });
  }
  if (stats.starterRatio[0]) {
    cards.push({ question: 'Who starts more conversations?', winner: stats.starterRatio[0].name, percentage: stats.starterRatio[0].percentage });
  }
  return cards;
}

export async function analyze(
  msgs: ParsedMessage[],
  stats: Statistics,
  couple: Couple,
  packageId: string,
  provider: ModelProvider,
  log: (stage: string, extra?: Record<string, unknown>) => void = () => {},
): Promise<RelationshipProfile> {
  const tone = couple.tone;

  // Stage: inside jokes + dictionary.
  const jokeCandidates = extractJokeCandidates(msgs, stats);
  log('candidates.inside_jokes', { count: jokeCandidates.length });
  const jokesOut = await provider.generate({
    ...insideJokesPrompt,
    payload: { candidates: jokeCandidates.slice(0, 8), tone },
  });
  const dictOut = await provider.generate({
    ...dictionaryPrompt,
    payload: { candidates: jokeCandidates, tone },
  });
  const insideJokes = jokesOut.insideJokes.filter((j) => j.confidence >= config.insideJokeConfidenceThreshold);
  const dictionary = dictOut.dictionary.filter((d) => d.confidence >= config.insideJokeConfidenceThreshold);

  // Stage: eras.
  const eraBuckets = bucketEras(msgs, stats);
  log('candidates.eras', { count: eraBuckets.length });
  const erasOut = await provider.generate({ ...erasPrompt, payload: { eras: eraBuckets, tone } });

  // Stage: awards.
  const awardCandidates = extractAwards(stats);
  const awardsOut = await provider.generate({ ...awardsPrompt, payload: { awards: awardCandidates, tone } });

  // Stage: memorable moments.
  const momentCandidates = extractMemorable(msgs);
  const momentsOut = await provider.generate({ ...memorablePrompt, payload: { moments: momentCandidates, tone } });

  // Stage: communication summary + who-cards.
  const whoCards = buildWhoCards(stats);
  const topPerson = [...stats.perPerson].sort((a, b) => b.messages - a.messages)[0];
  const commOut = await provider.generate({
    ...communicationPrompt,
    payload: {
      totalMessages: stats.totalMessages,
      topPersonName: topPerson?.name ?? couple.partnerA,
      topPersonPct: topPerson?.percentage ?? 50,
      whoCards,
    },
  });

  // Stage: DNA (deterministic) + archetypes.
  const dnaSignals = computeDnaSignals(msgs, stats);
  const dnaOut = await provider.generate({
    task: 'dna_adjust',
    version: '1.0.0',
    system: 'Adjust DNA dimension scores by at most ±15 based on tone; never invent.',
    prompt: 'Return the dimensions, optionally nudged, as {dimensions:[{name,score}]}.',
    payload: { dimensions: dnaSignals, tone },
    schema: (await import('zod')).z.object({
      dimensions: (await import('zod')).z.array(
        (await import('zod')).z.object({ name: (await import('zod')).z.string(), score: (await import('zod')).z.number() }),
      ),
    }),
  });

  const archetypes = {
    partnerA: computeArchetypes(msgs, couple.partnerA),
    partnerB: computeArchetypes(msgs, couple.partnerB),
  };

  // Stage: emoji interpretation.
  const emojiOut = await provider.generate({
    task: 'emoji_interpretation',
    version: '1.0.0',
    system: 'Interpret a couple\'s top emojis playfully. Never diagnose.',
    prompt: 'Given top emojis, write one witty interpretation line. Return {top, interpretation}.',
    payload: { top: stats.topEmojis },
    schema: (await import('../profile/schema.js')).EmojiSchema,
  });

  // Stage: creative synthesis (uses the more expensive model in real mode).
  const years = stats.durationDays ? Math.round((stats.durationDays / 365) * 10) / 10 : null;
  const creativeOut = await provider.generate({
    ...creativePrompt,
    model: config.ai.synthesisModel,
    payload: {
      partnerA: couple.partnerA,
      partnerB: couple.partnerB,
      totalMessages: stats.totalMessages,
      years,
      tone,
    },
  });

  // Timeline: provided milestones + first/last message. No invented events.
  const timeline: RelationshipProfile['timeline'] = [];
  const addProvided = (date: string | null | undefined, label: string) => {
    if (date) timeline.push({ date, label, kind: 'provided', confidence: 1 });
  };
  if (stats.firstMessageDate) timeline.push({ date: stats.firstMessageDate, label: 'First message', kind: 'detected', confidence: 1 });
  addProvided(couple.firstDate, 'First date');
  addProvided(couple.firstTrip, 'First trip');
  addProvided(couple.relationshipStartDate, 'Made it official');
  addProvided(couple.anniversaryDate, 'Anniversary');
  addProvided(couple.weddingDate, 'Wedding');
  if (stats.lastMessageDate) timeline.push({ date: stats.lastMessageDate, label: 'Latest message', kind: 'detected', confidence: 1 });
  timeline.sort((a, b) => (a.date && b.date ? a.date.localeCompare(b.date) : 0));

  const fp = buildFingerprintSignals(stats);

  const quotes = momentsOut.memorableMoments.flatMap((m) => m.quotes).slice(0, 6);

  const profile = {
    schemaVersion: 1 as const,
    generatedAt: new Date().toISOString(),
    packageId,
    couple,
    statistics: stats as unknown as Record<string, unknown>,
    communication: commOut,
    emojis: emojiOut,
    words: { top: stats.topWords },
    insideJokes,
    relationshipEras: erasOut.relationshipEras,
    awards: awardsOut.awards,
    memorableMoments: momentsOut.memorableMoments,
    dictionary,
    relationshipDna: {
      disclaimer: 'For entertainment and memory-keeping purposes.',
      dimensions: dnaOut.dimensions.map((d) => ({ name: d.name, score: Math.max(0, Math.min(100, Math.round(d.score))) })),
      archetypes,
    },
    quotes,
    timeline,
    fingerprint: fp,
    creativeSummary: creativeOut,
  };

  log('profile.assembled');
  return RelationshipProfileSchema.parse(profile);
}
