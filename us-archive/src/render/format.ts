/** Presentation helpers shared by the magazine and social renderers. */

export function num(n: number | undefined | null): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '0';
  return Math.round(n).toLocaleString('en-US');
}

export function humanDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

export function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number);
  if (!y || !m) return ym;
  return new Date(y, m - 1, 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export function hourLabel(h: number): string {
  const ampm = h < 12 ? 'AM' : 'PM';
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr} ${ampm}`;
}

export const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
