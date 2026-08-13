import { describe, it, expect } from 'vitest';
import { parseWhatsApp } from '../src/parser/whatsapp.js';
import { filterForOutput, screenMessage, containsSensitive } from '../src/privacy/redact.js';
import { isPastRetention } from '../src/pipeline/orchestrator.js';

describe('privacy filtering', () => {
  it('SAFE mode excludes messages with phone numbers and IDs', () => {
    const r = parseWhatsApp(
      [
        '15/06/2022, 21:45 - Alex: call me at +90 532 123 45 67',
        '15/06/2022, 21:46 - Mia: love you ❤️',
        '15/06/2022, 21:47 - Alex: my email is test@example.com',
      ].join('\n'),
    );
    const safe = filterForOutput(r.messages, 'SAFE');
    expect(safe.map((m) => m.message)).toEqual(['love you ❤️']);
  });

  it('NORMAL mode keeps all text messages', () => {
    const r = parseWhatsApp('15/06/2022, 21:45 - Alex: call +90 532 123 45 67');
    const normal = filterForOutput(r.messages, 'NORMAL');
    expect(normal.length).toBe(1);
  });

  it('flags sensitive categories', () => {
    const r = parseWhatsApp('15/06/2022, 21:45 - Alex: my password is hunter2');
    const screen = screenMessage(r.messages[0]);
    expect(screen.safe).toBe(false);
    expect(screen.categories).toContain('financial');
    expect(containsSensitive('IBAN TR12 3456 7890 1234 5678 90')).toBe(true);
  });

  it('retention window purges raw data after the configured days', () => {
    const old = new Date(Date.now() - 30 * 86400000);
    const recent = new Date();
    expect(isPastRetention(old)).toBe(true);
    expect(isPastRetention(recent)).toBe(false);
  });
});
