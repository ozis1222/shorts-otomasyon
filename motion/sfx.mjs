#!/usr/bin/env node
// Özgün sentez ses efektleri (örnek dosya yok, lisans sorunu yok). Tohumlu: her çalıştırmada aynı çıktı.
// Kullanım: node sfx.mjs <klasör> [yatak_süresi_sn]
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const SR = 48000, TAU = 2 * Math.PI, out = process.argv[2], BED = +(process.argv[3] || 60);
const buf = s => new Float64Array(Math.round(SR * s));
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function gauss(r) { const u = Math.max(r(), 1e-9), v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v); }
const noise = (sec, seed) => { const r = rng(seed), x = buf(sec); for (let i = 0; i < x.length; i++) x[i] = gauss(r); return x; };
function coef(type, f, Q) { const w = TAU * Math.min(f, SR * .45) / SR, c = Math.cos(w), s = Math.sin(w), al = s / (2 * Q); let b0, b1, b2; if (type === 'lp') { b0 = (1 - c) / 2; b1 = 1 - c; b2 = b0; } else if (type === 'hp') { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = b0; } else { b0 = al; b1 = 0; b2 = -al; } const a0 = 1 + al; return [b0 / a0, b1 / a0, b2 / a0, -2 * c / a0, (1 - al) / a0]; }
function filt(x, type, f, Q = .707) { const y = new Float64Array(x.length), fn = typeof f === 'function'; let k = coef(type, fn ? f(0) : f, Q), x1 = 0, x2 = 0, y1 = 0, y2 = 0; for (let i = 0; i < x.length; i++) { if (fn && i % 32 === 0) k = coef(type, f(i), Q); const v = k[0] * x[i] + k[1] * x1 + k[2] * x2 - k[3] * y1 - k[4] * y2; x2 = x1; x1 = x[i]; y2 = y1; y1 = v; y[i] = v; } return y; }
const peak = a => a.reduce((m, v) => Math.max(m, Math.abs(v)), 0) || 1;
function verb(x, { mix = .35, size = 1, fb = .84, tail = 2.5, damp = .3 } = {}) {
  const n = x.length + Math.round(tail * SR), wet = new Float64Array(n);
  for (const d0 of [1687, 1601, 2053, 2251, 1867]) { const d = Math.round(d0 * size), line = new Float64Array(d); let p = 0, lp = 0; for (let i = 0; i < n; i++) { const o = line[p]; lp += damp * (o - lp); line[p] = (x[i] || 0) + lp * fb; p = (p + 1) % d; wet[i] += o; } }
  let y = wet; for (const [d0, g] of [[347, .6], [113, .6]]) { const d = Math.round(d0 * size), line = new Float64Array(d), z = new Float64Array(n); let p = 0; for (let i = 0; i < n; i++) { const b = line[p], v = y[i] + g * b; z[i] = b - g * v; line[p] = v; p = (p + 1) % d; } y = z; }
  const k = mix * peak(x) / peak(y), o = new Float64Array(n); for (let i = 0; i < n; i++) o[i] = (x[i] || 0) + k * y[i]; return o;
}
function wav(name, x, db = -3) {
  const g = 10 ** (db / 20) / peak(x), fade = Math.round(SR * .02), n = x.length, b = Buffer.alloc(44 + n * 2);
  b.write('RIFF', 0); b.writeUInt32LE(36 + n * 2, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(SR, 24); b.writeUInt32LE(SR * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) { let v = x[i] * g; if (i > n - fade) v *= (n - i) / fade; if (i < fade) v *= i / fade; b.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(v * 32767))), 44 + i * 2); }
  writeFileSync(join(out, name + '.wav'), b);
}
// Orman ambiyansı: yumuşak rüzgâr, yaprak hışırtısı kabarmaları
function ambience() {
  const d = BED, w = filt(noise(d, 3), 'bp', i => 300 + 250 * (.5 + .5 * Math.sin(TAU * i / SR / 9)), .6), lv = filt(noise(d, 4), 'hp', 2500), x = buf(d);
  for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = w[i] * (.6 + .4 * Math.sin(TAU * t / 7.3)) + .25 * lv[i] * Math.max(0, Math.sin(TAU * t / 5.1 + 1)) ** 3; }
  return x;
}
function drone() {
  const d = BED, br = filt(noise(d, 5), 'lp', 120), x = buf(d);
  for (let i = 0; i < x.length; i++) { const t = i / SR, sw = .55 + .45 * Math.sin(TAU * t / 13 - 1); x[i] = (.45 * Math.sin(TAU * 43 * t) + .4 * Math.sin(TAU * 43.6 * t) + .1 * Math.sin(TAU * 64.5 * t)) * (.4 + .6 * Math.min(1, t / 20)) + .8 * br[i] * sw; }
  return x;
}
function wind() { const d = 6, x = filt(noise(d, 9), 'bp', i => 420 + 300 * Math.sin(TAU * i / SR / 3), .8); for (let i = 0; i < x.length; i++) x[i] *= Math.sin(Math.PI * i / x.length) ** 1.5; return x; }
function bird() { // uzak, seyrek ötüş
  const x = buf(1.2), r = rng(17); let o = 0;
  for (let n = 0; n < 3; n++) { const f0 = 2600 + r() * 900, len = .07 + r() * .05; let ph = 0; for (let i = 0; i < len * SR; i++) { const t = i / SR, f = f0 + 900 * Math.sin(Math.PI * t / len) - 600 * t / len; ph += TAU * f / SR; x[Math.round(o * SR) + i] += Math.sin(ph) * Math.sin(Math.PI * t / len) ** 2; } o += len + .05 + r() * .06; }
  return verb(filt(x, 'lp', 5000), { mix: .5, size: 1.2, tail: 1.5 });
}
function steps() { // yaprak ve toprakta birkaç adım
  const x = buf(2.4), r = rng(23);
  for (let k = 0; k < 4; k++) { const o = Math.round((.1 + k * .55) * SR), c = filt(noise(.3, 30 + k), 'bp', 1300 + r() * 500, .7); for (let i = 0; i < c.length; i++) { const t = i / SR; x[o + i] += c[i] * Math.exp(-t / .05) + .8 * Math.sin(TAU * (70 + 40 * Math.exp(-t / .02)) * t) * Math.exp(-t / .03); } }
  return verb(x, { mix: .3, size: .9, tail: 1 });
}
function radio() { // telsiz cızırtısı ve anlaşılmaz konuşma
  const d = 1.4, x = buf(d), n = filt(noise(d, 41), 'bp', 1800, .9), v = filt(noise(d, 42), 'bp', i => 900 + 500 * Math.sin(TAU * i / SR * 5), 3);
  for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = (t < .12 || t > d - .12 ? n[i] * 1.4 : .35 * n[i] + 1.2 * v[i] * (.5 + .5 * Math.sin(TAU * 4.3 * t))) * Math.min(1, t / .01); }
  return filt(x, 'hp', 400);
}
function swell() { const d = 3, x = buf(d), n = filt(noise(d, 51), 'lp', i => 150 + 900 * (i / (d * SR)) ** 2); for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = (n[i] + .4 * Math.sin(TAU * 55 * t)) * (t / d) ** 2 * Math.min(1, (d - t) / .2); } return verb(x, { mix: .3, tail: 1.5 }); }
function tone() { const d = 3, x = buf(d); for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = (Math.sin(TAU * 220 * t) + .6 * Math.sin(TAU * 233 * t) + .3 * Math.sin(TAU * 330 * t)) * Math.min(1, t / .8) * Math.exp(-Math.max(0, t - 1) / .9); } return verb(x, { mix: .5, tail: 2 }); }
function beep() { const x = buf(.35); for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = Math.sign(Math.sin(TAU * 4000 * t)) * .3 * (t < .08 || (t > .14 && t < .22) ? 1 : 0); } return filt(x, 'lp', 7000); }
function whisper() {
  const d = 2.2, n = noise(d, 61), a = filt(n, 'bp', i => 1900 + 800 * Math.sin(TAU * i / SR * 2.1), 2.5), s = filt(n, 'hp', 5000), x = buf(d);
  for (const [o, len, ss] of [[.1, .3], [.5, .45, 1], [1.1, .5]]) { const o0 = Math.round(o * SR), L = Math.round(len * SR); for (let i = 0; i < L; i++) { const e = Math.sin(Math.PI * i / L) ** 2; x[o0 + i] += a[o0 + i] * e + (ss ? .6 * s[o0 + i] * e : 0); } }
  return verb(x, { mix: .9, size: 1.4, fb: .86, tail: 2.5 });
}
function lowHit() { const x = buf(1.6), n = filt(noise(1.6, 71), 'lp', 300); for (let i = 0; i < x.length; i++) { const t = i / SR; x[i] = Math.sin(TAU * (32 + 40 * Math.exp(-t / .07)) * t) * Math.exp(-t / .55) + .5 * n[i] * Math.exp(-t / .07); } return verb(x, { mix: .45, size: 1.3, tail: 2.5 }); }

mkdirSync(out, { recursive: true });
const SFX = { ambience, drone, wind, bird, steps, radio, swell, tone, beep, whisper, low_hit: lowHit };
for (const [k, f] of Object.entries(SFX)) wav(k, f());
