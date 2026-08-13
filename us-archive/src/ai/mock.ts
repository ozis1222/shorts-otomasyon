/**
 * Offline synthesizer. Given the same deterministic candidate payloads the real
 * LLM would receive, it produces well-formed, tone-aware output — so `npm run
 * demo` yields a complete, non-placeholder product with no API key. It phrases
 * only what the deterministic layer already found; it never invents evidence.
 */

type Tone = 'romantic' | 'funny' | 'balanced' | 'minimal' | 'emotional';

function pick<T>(arr: T[], seed: number): T {
  return arr[Math.abs(seed) % arr.length];
}

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function synthesizeMock(task: string, payload: any): unknown {
  switch (task) {
    case 'inside_jokes':
      return mockInsideJokes(payload);
    case 'dictionary':
      return mockDictionary(payload);
    case 'eras':
      return mockEras(payload);
    case 'awards':
      return mockAwards(payload);
    case 'memorable':
      return mockMemorable(payload);
    case 'communication_summary':
      return mockCommunication(payload);
    case 'emoji_interpretation':
      return mockEmoji(payload);
    case 'dna_adjust':
      return { dimensions: payload.dimensions };
    case 'creative':
      return mockCreative(payload);
    default:
      throw new Error(`Mock synthesizer has no handler for task "${task}"`);
  }
}

function mockInsideJokes(payload: { candidates: any[]; tone: Tone }) {
  const jokes = (payload.candidates || []).slice(0, 8).map((c: any) => {
    const templates = [
      `A word that keeps resurfacing whenever the mood turns playful — used ${c.count} times and counting.`,
      `Historical evidence across ${c.count} messages suggests this means something only the two of you fully understand.`,
      `Appears ${c.count} times, almost always right before something ridiculous happens.`,
    ];
    return {
      term: String(c.term).toUpperCase(),
      definition: pick(templates, hash(c.term)),
      confidence: Math.min(0.95, 0.55 + c.count / 200),
      evidenceIds: (c.evidenceIds || []).slice(0, 5),
    };
  });
  return { insideJokes: jokes };
}

function mockDictionary(payload: { candidates: any[]; tone: Tone }) {
  const entries = (payload.candidates || []).slice(0, 10).map((c: any) => ({
    term: String(c.term).toUpperCase(),
    definition: pick(
      [
        `Recurring vocabulary of this relationship. Frequency: ${c.count}.`,
        `A shared shorthand — meaning drifts, usage does not.`,
        `Officially untranslatable outside this chat. Seen ${c.count} times.`,
      ],
      hash(c.term),
    ),
    confidence: Math.min(0.9, 0.5 + c.count / 150),
    evidenceIds: (c.evidenceIds || []).slice(0, 5),
  }));
  return { dictionary: entries };
}

function mockEras(payload: { eras: any[]; tone: Tone }) {
  const eras = (payload.eras || []).map((e: any) => ({
    title: e.title,
    startDate: e.startDate ?? null,
    endDate: e.endDate ?? null,
    description: `${e.messageCount} messages defined this stretch${
      e.topWords?.length ? `, circling around "${e.topWords.slice(0, 3).join('", "')}"` : ''
    }.`,
    messageCount: e.messageCount || 0,
    highlight: e.topWords?.[0] ? `Recurring theme: ${e.topWords[0]}` : '',
  }));
  return { relationshipEras: eras };
}

function mockAwards(payload: { awards: any[]; tone: Tone }) {
  const awards = (payload.awards || []).map((a: any) => ({
    category: a.category,
    winner: a.winner,
    blurb: a.stat
      ? `${a.winner}, decisively. ${a.stat}`
      : `${a.winner} takes this one, no contest.`,
  }));
  return { awards };
}

function mockMemorable(payload: { moments: any[]; tone: Tone }) {
  const moments = (payload.moments || []).map((m: any) => ({
    title: m.title,
    description: m.description || 'One of those small exchanges that says everything.',
    quotes: (m.quotes || []).map((q: any) => ({
      messageId: q.messageId,
      sender: q.sender,
      text: q.text,
    })),
  }));
  return { memorableMoments: moments };
}

function mockCommunication(payload: any) {
  const { totalMessages, topPersonName, topPersonPct } = payload;
  return {
    summary:
      `Across ${totalMessages.toLocaleString()} messages, the rhythm is unmistakably yours. ` +
      `${topPersonName} sends a touch more (${topPersonPct}%), but the back-and-forth stays balanced ` +
      `— a conversation that never really stopped.`,
    whoCards: payload.whoCards || [],
  };
}

function mockEmoji(payload: any) {
  const top = payload.top?.[0]?.emoji || '❤️';
  return {
    top: payload.top || [],
    interpretation: `Your love language is roughly 40% words, 60% ${top}.`,
  };
}

function mockCreative(payload: any) {
  const { partnerA, partnerB, totalMessages, years, tone } = payload;
  const closings: Record<Tone, string> = {
    romantic: 'Every message was a small way of saying: I choose you, again.',
    funny: 'Thousands of messages later, still arguing about where to eat. Never change.',
    balanced: 'Thousands of messages. One story. Yours.',
    minimal: 'This is what it looked like.',
    emotional: 'You wrote this together, one message at a time.',
  };
  return {
    coverTitle: `${partnerA} & ${partnerB}`,
    coverSubtitle: `${Number(totalMessages).toLocaleString()} messages${
      years ? ` over ${years} years` : ''
    }.`,
    ifWeWere: [
      { prompt: 'If we were a time of day…', answer: 'Late night, phones lighting up two faces.' },
      { prompt: 'If we were a genre…', answer: 'A slow-burn with excellent comic relief.' },
      { prompt: 'If we were a weather forecast…', answer: 'Mostly warm, occasional dramatic storms, quick to clear.' },
    ],
    futureLetter:
      `To future ${partnerA} and ${partnerB}: whatever changed, remember it started as words on a screen — ` +
      `and somehow became a whole life. Keep texting each other like this.`,
    closingLine: closings[tone as Tone] || closings.balanced,
  };
}
