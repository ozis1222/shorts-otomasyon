import { describe, it, expect } from 'vitest';
import { parseWhatsApp } from '../src/parser/whatsapp.js';
import { computeStatistics } from '../src/stats/statistics.js';

function build(lines: string[]): string {
  return lines.join('\n');
}

describe('statistics', () => {
  it('counts messages and per-person percentages deterministically', () => {
    const r = parseWhatsApp(
      build([
        '15/06/2022, 21:45 - Alex: hello there',
        '15/06/2022, 21:46 - Alex: you up?',
        '15/06/2022, 21:47 - Mia: yes',
      ]),
    );
    const s = computeStatistics(r.messages);
    expect(s.totalMessages).toBe(3);
    const alex = s.perPerson.find((p) => p.name === 'Alex')!;
    const mia = s.perPerson.find((p) => p.name === 'Mia')!;
    expect(alex.messages).toBe(2);
    expect(mia.messages).toBe(1);
    expect(alex.percentage).toBeCloseTo(66.7, 1);
    expect(alex.doubleTexts).toBe(1); // two Alex messages in a row
  });

  it('detects late-night messages (00:00–04:59)', () => {
    const r = parseWhatsApp(
      build([
        '15/06/2022, 02:30 - Alex: you awake?',
        '15/06/2022, 14:00 - Mia: at work',
      ]),
    );
    const s = computeStatistics(r.messages);
    expect(s.lateNightMessages).toBe(1);
  });

  it('counts questions and emojis', () => {
    const r = parseWhatsApp(
      build([
        '15/06/2022, 21:45 - Alex: how are you? 😍',
        '15/06/2022, 21:46 - Mia: good 😍😂',
      ]),
    );
    const s = computeStatistics(r.messages);
    expect(s.questionsAsked).toBe(1);
    const topEmoji = s.topEmojis[0];
    expect(topEmoji.emoji).toBe('😍');
    expect(topEmoji.count).toBe(2);
  });

  it('identifies conversation starters via session gaps', () => {
    const r = parseWhatsApp(
      build([
        '15/06/2022, 09:00 - Alex: morning',
        '15/06/2022, 09:01 - Mia: morning',
        // 8h gap -> new session started by Mia
        '15/06/2022, 18:00 - Mia: dinner?',
        '15/06/2022, 18:01 - Alex: yes',
      ]),
    );
    const s = computeStatistics(r.messages);
    expect(s.totalSessions).toBe(2);
    const alexStart = s.starterRatio.find((x) => x.name === 'Alex')!;
    const miaStart = s.starterRatio.find((x) => x.name === 'Mia')!;
    expect(alexStart.percentage).toBe(50);
    expect(miaStart.percentage).toBe(50);
  });
});
