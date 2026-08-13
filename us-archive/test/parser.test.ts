import { describe, it, expect } from 'vitest';
import { parseWhatsApp } from '../src/parser/whatsapp.js';

describe('WhatsApp parser', () => {
  it('parses the dashed DMY 24h format', () => {
    const raw = [
      '15/06/2022, 21:45 - Alex: hey 🙂',
      '15/06/2022, 21:46 - Mia: hi babe ❤️',
    ].join('\n');
    const r = parseWhatsApp(raw);
    expect(r.meta.parsedMessages).toBe(2);
    expect(r.participants.sort()).toEqual(['Alex', 'Mia']);
    expect(r.messages[0].emoji).toContain('🙂');
    expect(r.messages[1].emoji).toContain('❤️');
    expect(r.meta.dateOrder).toBe('DMY');
  });

  it('parses the bracketed 12h AM/PM format with seconds', () => {
    const raw = [
      '[6/15/22, 9:45:07 PM] Alex: good night',
      '[6/16/22, 12:15:00 AM] Mia: still awake?',
    ].join('\n');
    const r = parseWhatsApp(raw);
    expect(r.meta.parsedMessages).toBe(2);
    // 9:45 PM -> hour 21
    expect(new Date(r.messages[0].timestamp).getHours()).toBe(21);
    // 12:15 AM -> hour 0
    expect(new Date(r.messages[1].timestamp).getHours()).toBe(0);
  });

  it('auto-detects MDY when the first field exceeds 12', () => {
    const raw = '12/25/2022, 10:00 - Alex: merry christmas';
    const r = parseWhatsApp(raw);
    expect(r.meta.dateOrder).toBe('MDY');
    const d = new Date(r.messages[0].timestamp);
    expect(d.getMonth()).toBe(11); // December
    expect(d.getDate()).toBe(25);
  });

  it('joins multiline messages', () => {
    const raw = [
      '15/06/2022, 21:45 - Alex: line one',
      'line two',
      'line three',
      '15/06/2022, 21:46 - Mia: ok',
    ].join('\n');
    const r = parseWhatsApp(raw);
    expect(r.meta.parsedMessages).toBe(2);
    expect(r.messages[0].message).toBe('line one\nline two\nline three');
  });

  it('classifies media, voice and deleted placeholders', () => {
    const raw = [
      '15/06/2022, 21:45 - Alex: <Media omitted>',
      '15/06/2022, 21:46 - Mia: voice message (0:14)',
      '15/06/2022, 21:47 - Alex: This message was deleted',
      '15/06/2022, 21:48 - Mia: sticker omitted',
    ].join('\n');
    const r = parseWhatsApp(raw);
    const types = r.messages.map((m) => m.type);
    expect(types).toContain('media');
    expect(types).toContain('voice');
    expect(types).toContain('deleted');
    expect(types).toContain('sticker');
  });

  it('treats system lines as system, not people', () => {
    const raw = [
      '15/06/2022, 21:44 - Messages and calls are end-to-end encrypted.',
      '15/06/2022, 21:45 - Alex: hi',
    ].join('\n');
    const r = parseWhatsApp(raw);
    expect(r.participants).toEqual(['Alex']);
    expect(r.meta.systemMessages).toBeGreaterThanOrEqual(1);
  });

  it('handles Turkish characters and names', () => {
    const raw = '15/06/2022, 21:45 - Ayşe: günaydın canım ☕';
    const r = parseWhatsApp(raw);
    expect(r.participants).toEqual(['Ayşe']);
    expect(r.messages[0].message).toContain('günaydın');
  });
});
