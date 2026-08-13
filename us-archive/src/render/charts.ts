/** Minimal, dependency-free inline-SVG charts tuned for the editorial look. */
import type { Theme } from './theme.js';

export function esc(s: string): string {
  return String(s).replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&#39;', '"': '&quot;' })[c]!);
}

/** Horizontal bar chart. Values are labeled; the max bar fills the track. */
export function barChart(
  data: { label: string; value: number }[],
  theme: Theme,
  opts: { width?: number; barHeight?: number; format?: (n: number) => string } = {},
): string {
  const width = opts.width ?? 620;
  const bh = opts.barHeight ?? 34;
  const gap = 14;
  const max = Math.max(...data.map((d) => d.value), 1);
  const labelW = 150;
  const trackW = width - labelW - 70;
  const rows = data
    .map((d, i) => {
      const y = i * (bh + gap);
      const w = Math.max(2, (d.value / max) * trackW);
      const color = theme.accents[i % theme.accents.length];
      const val = opts.format ? opts.format(d.value) : String(d.value);
      return `
        <g transform="translate(0, ${y})">
          <text x="0" y="${bh / 2 + 5}" font-family="${theme.sans}" font-size="15" fill="${theme.inkSoft}">${esc(d.label)}</text>
          <rect x="${labelW}" y="0" width="${trackW}" height="${bh}" rx="6" fill="${theme.hair}" opacity="0.5"/>
          <rect x="${labelW}" y="0" width="${w}" height="${bh}" rx="6" fill="${color}"/>
          <text x="${labelW + w + 10}" y="${bh / 2 + 5}" font-family="${theme.sans}" font-size="14" font-weight="600" fill="${theme.ink}">${esc(val)}</text>
        </g>`;
    })
    .join('');
  const h = data.length * (bh + gap);
  return `<svg width="${width}" height="${h}" viewBox="0 0 ${width} ${h}" xmlns="http://www.w3.org/2000/svg">${rows}</svg>`;
}

/** 24-column "activity by hour" columns. */
export function hourColumns(byHour: number[], theme: Theme, width = 640, height = 180): string {
  const max = Math.max(...byHour, 1);
  const n = byHour.length;
  const cw = width / n;
  const bars = byHour
    .map((v, i) => {
      const h = Math.max(1, (v / max) * (height - 30));
      const x = i * cw;
      const isPeak = v === max;
      return `<rect x="${x + 2}" y="${height - 20 - h}" width="${cw - 4}" height="${h}" rx="2" fill="${isPeak ? theme.accent : theme.accent2}" opacity="${isPeak ? 1 : 0.55}"/>` +
        (i % 6 === 0 ? `<text x="${x + cw / 2}" y="${height - 4}" text-anchor="middle" font-family="${theme.sans}" font-size="11" fill="${theme.inkSoft}">${i}:00</text>` : '');
    })
    .join('');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">${bars}</svg>`;
}

/** Radar / spider chart for the Relationship DNA dimensions. */
export function radarChart(
  dims: { name: string; score: number }[],
  theme: Theme,
  size = 460,
): string {
  // Extra horizontal room so long axis labels never clip at the SVG edge.
  const pad = Math.round(size * 0.34);
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.3;
  const n = dims.length;
  const angle = (i: number) => (i / n) * Math.PI * 2 - Math.PI / 2;
  const point = (i: number, v: number) => {
    const rr = r * (v / 100);
    return [cx + Math.cos(angle(i)) * rr, cy + Math.sin(angle(i)) * rr];
  };
  const grid = [0.25, 0.5, 0.75, 1]
    .map((g) => {
      const pts = dims.map((_, i) => {
        const x = cx + Math.cos(angle(i)) * r * g;
        const y = cy + Math.sin(angle(i)) * r * g;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
      return `<polygon points="${pts}" fill="none" stroke="${theme.hair}" stroke-width="1"/>`;
    })
    .join('');
  const spokes = dims.map((_, i) => {
    const x = cx + Math.cos(angle(i)) * r;
    const y = cy + Math.sin(angle(i)) * r;
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${theme.hair}" stroke-width="1"/>`;
  }).join('');
  const shape = dims.map((d, i) => point(i, d.score).map((n2) => n2.toFixed(1)).join(',')).join(' ');
  const labels = dims.map((d, i) => {
    const x = cx + Math.cos(angle(i)) * (r + 26);
    const y = cy + Math.sin(angle(i)) * (r + 26);
    const anchor = Math.abs(Math.cos(angle(i))) < 0.3 ? 'middle' : Math.cos(angle(i)) > 0 ? 'start' : 'end';
    return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${anchor}" dominant-baseline="middle" font-family="${theme.sans}" font-size="13" font-weight="600" fill="${theme.ink}">${esc(d.name)}</text>` +
      `<text x="${x.toFixed(1)}" y="${(y + 16).toFixed(1)}" text-anchor="${anchor}" dominant-baseline="middle" font-family="${theme.sans}" font-size="11" fill="${theme.inkSoft}">${d.score}</text>`;
  }).join('');
  const vbW = size + pad * 2;
  return `<svg width="${vbW}" height="${size}" viewBox="${-pad} 0 ${vbW} ${size}" xmlns="http://www.w3.org/2000/svg">${grid}${spokes}<polygon points="${shape}" fill="${theme.accent}" fill-opacity="0.28" stroke="${theme.accent}" stroke-width="2.5"/>${labels}</svg>`;
}

/** Donut showing message split between two people. */
export function splitDonut(a: { name: string; pct: number }, b: { name: string; pct: number }, theme: Theme, size = 220): string {
  const r = size / 2 - 20;
  const c = 2 * Math.PI * r;
  const aLen = (a.pct / 100) * c;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(${size / 2}, ${size / 2}) rotate(-90)">
      <circle r="${r}" fill="none" stroke="${theme.accent2}" stroke-width="26"/>
      <circle r="${r}" fill="none" stroke="${theme.accent}" stroke-width="26" stroke-dasharray="${aLen} ${c}"/>
    </g>
    <text x="${size / 2}" y="${size / 2 - 4}" text-anchor="middle" font-family="${theme.sans}" font-size="26" font-weight="700" fill="${theme.ink}">${a.pct}%</text>
    <text x="${size / 2}" y="${size / 2 + 18}" text-anchor="middle" font-family="${theme.sans}" font-size="13" fill="${theme.inkSoft}">${esc(a.name)}</text>
  </svg>`;
}
