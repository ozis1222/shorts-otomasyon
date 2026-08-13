/**
 * Synthetic WhatsApp chat generator. Produces a realistic-but-entirely-fake
 * export (in real WhatsApp .txt format, so it exercises the actual parser) with
 * inside jokes, trips, late-night talks, food debates, romance and squabbles
 * across distinct eras. Fully seeded — same seed ⇒ same chat.
 */

export interface SyntheticOptions {
  partnerA?: string;
  partnerB?: string;
  startDate?: Date;
  months?: number;
  targetMessages?: number;
  seed?: number;
}

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const GREETINGS = ['hey', 'heyy', 'good morning ☀️', 'morninggg', 'you up?', 'hiii', 'gm', 'hello love ❤️'];
const AFFECTION = ['i miss you 🥰', 'love you', 'love you too ❤️', 'cant wait to see you', 'thinking about you', 'youre the best', 'miss your face 😘', 'come home already 🥺'];
const HUMOR = ['STOP 😂😂', 'im crying lmao', 'you did NOT just say that', 'hahahaha', 'why are you like this 😭', 'im deceased 💀', 'the audacity 😂', 'thats so random lol'];
const FOOD = ['what do you want to eat', 'idk what do YOU want', 'not helpful', 'pizza?', 'we had pizza yesterday', 'potato it is then 🥔', 'POTATO', 'im fine with anything', 'youre never fine with anything 😂', 'sushi?', 'too expensive', 'fine burgers'];
const PLANNING = ['what time tomorrow?', 'give me 5 minutes', 'you said 5 minutes 20 min ago', 'ill be there at 8', 'book the table?', 'done, 8pm', 'dont forget the tickets', 'already have them 😌'];
const DEEP = ['do you ever think about where well be in 10 years', 'all the time honestly', 'i feel like we can do anything together', 'what does home even mean to you', 'wherever you are', 'thats so cheesy 😂 but same'];
const CHAOS = ['OMG', 'you will NOT believe what just happened', 'what what what', 'ok so', 'i dropped my phone in the toilet 💀', 'NO', 'YES', 'im screaming'];
const TRAVEL = ['this view is unreal 😍', 'best trip ever', 'we HAVE to come back here', 'sunset was insane tonight', 'i never want to leave', 'the flight was 3 hours late ugh', 'worth it though'];
const NIGHT = ['you asleep?', 'no youre here 🙂', 'cant sleep', 'come over', 'its 3am babe', 'i know 🌙', 'one more episode?', 'you said that 2 episodes ago 😂'];
const QUESTIONS = ['did you eat?', 'how was work?', 'you okay?', 'call me later?', 'what are you doing?', 'coffee tomorrow?'];

const CATEGORIES = [GREETINGS, AFFECTION, HUMOR, FOOD, PLANNING, DEEP, CHAOS, TRAVEL, NIGHT, QUESTIONS];

function two(n: number): string {
  return String(n).padStart(2, '0');
}

/** Weighted random hour — evenings & late night dominate. */
function pickHour(rnd: () => number): number {
  const weights = [3, 2, 2, 1, 1, 1, 2, 4, 6, 6, 5, 6, 7, 6, 5, 5, 6, 7, 9, 10, 10, 9, 7, 5];
  const total = weights.reduce((a, b) => a + b, 0);
  let r = rnd() * total;
  for (let h = 0; h < 24; h++) {
    r -= weights[h];
    if (r <= 0) return h;
  }
  return 21;
}

export function generateSyntheticChat(opts: SyntheticOptions = {}): string {
  const a = opts.partnerA ?? 'Alex';
  const b = opts.partnerB ?? 'Mia';
  const start = opts.startDate ?? new Date(2022, 5, 1, 9, 0, 0);
  const months = opts.months ?? 36;
  const target = opts.targetMessages ?? 25000;
  const rnd = mulberry32(opts.seed ?? 42);

  const endMs = new Date(start.getFullYear(), start.getMonth() + months, start.getDate()).getTime();
  const spanMs = endMs - start.getTime();
  const lines: string[] = [];

  lines.push(fmt(start, `Messages and calls are end-to-end encrypted.`, null));

  let count = 0;
  // Walk day by day; on active days emit a burst of a themed session.
  let cursor = new Date(start);
  while (cursor.getTime() < endMs && count < target) {
    // Activity ramps over the relationship (more messages as it deepens).
    const progress = (cursor.getTime() - start.getTime()) / spanMs;
    const dailyBase = 15 + progress * 20;
    const active = rnd() < 0.82;
    if (active) {
      const sessions = 1 + Math.floor(rnd() * 3);
      for (let sIdx = 0; sIdx < sessions && count < target; sIdx++) {
        const hour = pickHour(rnd);
        let minute = Math.floor(rnd() * 60);
        // Occasional vacation week => TRAVEL theme.
        const isTrip = progress > 0.2 && rnd() < 0.04;
        const cat = isTrip ? TRAVEL : CATEGORIES[Math.floor(rnd() * CATEGORIES.length)];
        const burst = Math.max(2, Math.round((dailyBase / sessions) * (0.5 + rnd())));
        let speaker = rnd() < 0.5 ? a : b;
        let t = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate(), hour, minute, Math.floor(rnd() * 60));
        for (let i = 0; i < burst && count < target; i++) {
          const msg = cat[Math.floor(rnd() * cat.length)];
          lines.push(fmt(t, msg, speaker));
          count++;
          // Occasional media / voice placeholders.
          if (rnd() < 0.05) {
            lines.push(fmt(t, '<Media omitted>', speaker));
            count++;
          }
          if (rnd() < 0.02) {
            lines.push(fmt(t, 'voice message (0:14)', speaker));
            count++;
          }
          // Sometimes double-text, usually switch speaker.
          if (rnd() > 0.35) speaker = speaker === a ? b : a;
          t = new Date(t.getTime() + (500 + rnd() * 240000)); // 0.5s–4min later
        }
      }
    }
    cursor = new Date(cursor.getTime() + 86400000);
  }

  return lines.join('\n') + '\n';
}

function fmt(d: Date, msg: string, sender: string | null): string {
  const date = `${two(d.getDate())}/${two(d.getMonth() + 1)}/${d.getFullYear()}`;
  const time = `${two(d.getHours())}:${two(d.getMinutes())}`;
  return sender ? `${date}, ${time} - ${sender}: ${msg}` : `${date}, ${time} - ${msg}`;
}
