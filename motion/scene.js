/* motion-engine sahne motoru (shorts-otomasyon).
 * Gemini'nin storyboard'unu (props.json: scenes/background/prop/characters, captions, cast...) sinematik olarak çizer.
 * motion-engine runtime sözleşmesi: render(t) saf fonksiyondur, HB.boot ile açılır; kareler motion/render.mjs ile alınır.
 * Arka planlar: plain room night forest sea sky office lab snow desert cave street
 * Yakın plan objeler: clock → saat, footprints → ayak izi, letter/map → belge. Diğer objeler sahnenin içine çizilir.
 */
const PR = window.PROPS, W = 1080, H = 1920, u = W / 720;
document.documentElement.style.setProperty('--w', W + 'px');
document.documentElement.style.setProperty('--h', H + 'px');
document.documentElement.style.setProperty('--ratio', `${W}/${H}`);
if (new URLSearchParams(location.search).has('play')) document.body.classList.add('preview');
const cv = document.querySelector('#film'); cv.width = W; cv.height = H;
const ctx = cv.getContext('2d');
const { clamp, lerp, ease, prog } = HB;
const TAU = Math.PI * 2;
const sm = (a, b, t) => { const p = clamp((t - a) / (b - a)); return p * p * (3 - 2 * p); };
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const noise = (x, s = 0) => { const i = Math.floor(x), f = x - i, k = f * f * (3 - 2 * f); return lerp(hash(i + s * 91.7), hash(i + 1 + s * 91.7), k) * 2 - 1; };
const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h); return c; };
function R(seed) { let s = seed >>> 0 || 1; return () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const mix = (a, b, p) => a.map((v, i) => lerp(v, b[i], p));
const hex = h => { const m = /^#?([0-9a-f]{6})$/i.exec(h || ''); return m ? [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16)) : null; };
const BLACK = [0, 0, 0], DEEP = [8, 11, 12], YEL = '#ffd23f', VY = H * .56;
const SEED = [...(PR.headline || 'x')].reduce((a, c) => a * 31 + c.charCodeAt(0) >>> 0, 7);

// ── Dokular ───────────────────────────────────────────────────────────
function tex(base, seed, n, light) {
  const S = 512, c = mk(S, S), g = c.getContext('2d'), r = R(seed);
  g.fillStyle = base; g.fillRect(0, 0, S, S);
  for (let i = 0; i < n; i++) {
    const x = r() * S, y = r() * S, rx = 2 + r() * 40, ry = rx * (.3 + r() * .7), l = light[0] + r() * light[1];
    g.fillStyle = `hsla(${24 + r() * 18},${6 + r() * 12}%,${l}%,${.08 + r() * .25})`;
    for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) { g.beginPath(); g.ellipse(x + ox, y + oy, rx, ry, r() * 3, 0, TAU); g.fill(); }
  }
  return ctx.createPattern(c, 'repeat');
}
const PAT = {};
const pat = (k, ...a) => PAT[k] || (PAT[k] = tex(...a));
const fogSprites = new Map();
function fogSprite(col, seed) {
  const key = col.join() + ':' + seed; if (fogSprites.has(key)) return fogSprites.get(key);
  const c = mk(1000 * u, 420 * u), g = c.getContext('2d'), r = R(seed);
  g.filter = `blur(${30 * u}px)`;
  for (let i = 0; i < 30; i++) { g.fillStyle = rgb(col, .05 + r() * .09); g.beginPath(); g.ellipse(c.width * (.15 + r() * .7), c.height * (.3 + r() * .4), (60 + r() * 220) * u, (20 + r() * 60) * u, 0, 0, TAU); g.fill(); }
  fogSprites.set(key, c); return c;
}
function drift(col, t, { y, speed = 14, n = 3, a = 1, seed = 1, scale = 1 }) {
  for (let i = 0; i < n; i++) {
    const sp = fogSprite(col, seed + i), span = W + sp.width * scale, x = ((i * span / n + t * speed * u * (1 + i * .3)) % span) - sp.width * scale;
    ctx.globalAlpha = a; ctx.drawImage(sp, x, y + Math.sin(t * .2 + i) * 12 * u - sp.height * scale / 2, sp.width * scale, sp.height * scale);
  }
  ctx.globalAlpha = 1;
}
function fogFill(col, a, y0 = 0, y1 = H, a2 = a) { const g = ctx.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, rgb(col, a)); g.addColorStop(1, rgb(col, a2)); ctx.fillStyle = g; ctx.fillRect(0, y0, W, y1 - y0); }
function blurred(c, px) { if (!px) return c; const o = mk(c.width, c.height), g = o.getContext('2d'); g.filter = `blur(${px}px)`; g.drawImage(c, 0, 0); return o; }
// depth: 1 yakın … 7 uzak. cam: {x, y, push, vx, vy}
function drawLayer(c, depth, cam) {
  const s = 1 + cam.push / depth, ox = -(c.width - W) / 2 - cam.x / depth;
  ctx.save(); ctx.translate(cam.vx, cam.vy); ctx.scale(s, s); ctx.translate(-cam.vx + ox, -cam.vy + (cam.y || 0) / depth); ctx.drawImage(c, 0, 0); ctx.restore();
}
const proj = (x, y, depth, cam) => { const s = 1 + cam.push / depth; return [cam.vx + (x - cam.x / depth - cam.vx) * s, cam.vy + (y - cam.vy) * s, s]; };

// ── Çam ormanı ────────────────────────────────────────────────────────
function pine(g, x, y, h, col, r, bare = .1) {
  const w = h * (.19 + r() * .07) * (1 - bare * .5), tw0 = h * (.011 + bare * .008);
  g.fillStyle = col; g.beginPath(); g.moveTo(x - tw0 * 1.4, y + 3); g.lineTo(x - tw0 * .6, y - h * .95); g.lineTo(x + tw0 * .6, y - h * .95); g.lineTo(x + tw0 * 1.4, y + 3); g.fill();
  const n = 14 + Math.floor(r() * 6), b0 = Math.max(.13, bare);
  for (let i = 0; i < n; i++) {
    const f = i / n, ty = y - h * (b0 + (.98 - b0) * f), tw = w * Math.pow(1 - f, .85) * (.78 + r() * .44) + h * .012, th = h * .14 * (1 - f * .55);
    g.beginPath();
    for (const sd of [-1, 1]) {
      g.moveTo(x, ty - th * .75);
      for (let k = 1; k <= 7; k++) { const q = k / 7; g.lineTo(x + sd * tw * q, ty - th * .75 + th * 1.15 * Math.pow(q, 1.5) + (r() - .5) * th * .32); }
      for (let k = 6; k >= 0; k--) { const q = k / 7; g.lineTo(x + sd * tw * q * (.96 + r() * .08), ty + th * (.22 + .25 * Math.pow(q, 1.3)) + (r() - .5) * th * .4); }
      g.closePath();
    }
    g.fill();
  }
}
function forest({ seed, w = W * 1.5, n, yMin, yMax, hMin, hMax, col, corridor = 0, bare = .1, blur = 0 }) {
  const c = mk(w, H), g = c.getContext('2d'), r = R(seed), cx = w / 2, items = [];
  for (let i = 0; i < n; i++) { let x = r() * w; if (corridor && Math.abs(x - cx) < corridor) x = cx + Math.sign(x - cx || 1) * (corridor + r() * corridor * .6); items.push([x, lerp(yMin, yMax, r()), lerp(hMin, hMax, r())]); }
  items.sort((a, b) => a[1] - b[1]).forEach(([x, y, h]) => pine(g, x, y, h, col, r, bare));
  return blurred(c, blur);
}
function forestSet(seed, fog, k = [.82, .7, .56, .42, .24, .08]) {
  return [7, 5.2, 3.8, 2.7, 1.9, 1.25].map((d, i) => ({ d, c: forest({ seed: seed + i, n: [70, 50, 34, 22, 14, 8][i], yMin: VY - 12 * u + i * 30 * u, yMax: VY + (20 + i * 120) * u, hMin: (220 + i * 260) * u, hMax: (340 + i * 520) * u, col: rgb(mix(DEEP, fog, k[i])), corridor: [30, 60, 110, 190, 300, 380][i] * u, bare: [.08, .1, .18, .3, .45, .55][i], blur: [3, 2, 0, 0, 3, 7][i] * u }) }));
}
function groundPath({ col, pathCol, fog, fogA = .6, w0 = 330 * u, w1 = 26 * u, seed = 3, horizon = VY }) {
  const c = mk(W * 1.5, H), g = c.getContext('2d'), cx = c.width / 2, r = R(seed);
  const gg = g.createLinearGradient(0, horizon, 0, H); gg.addColorStop(0, rgb(col)); gg.addColorStop(1, rgb(mix(col, BLACK, .45)));
  g.fillStyle = gg; g.fillRect(0, horizon - 4, c.width, H);
  if (pathCol) {
    g.save(); g.beginPath(); g.moveTo(cx - w1, horizon); g.lineTo(cx + w1, horizon); g.lineTo(cx + w0, H + 20); g.lineTo(cx - w0, H + 20); g.closePath(); g.clip();
    const pp = pat('mud', '#3a342b', 77, 2600, [12, 22]); pp.setTransform(new DOMMatrix().scale(1.3 * u)); g.fillStyle = pp; g.fillRect(0, horizon, c.width, H);
    const pg = g.createLinearGradient(0, horizon, 0, H); pg.addColorStop(0, rgb(pathCol, .8)); pg.addColorStop(1, rgb(pathCol, .25)); g.fillStyle = pg; g.fillRect(0, horizon, c.width, H);
    g.restore();
  }
  for (let i = 0; i < 700; i++) { const v = Math.pow(r(), 1.4), y = lerp(horizon, H, v), x = r() * c.width, l = lerp(2, 18, v) * u; g.strokeStyle = rgb(mix(col, BLACK, .3 + r() * .4), .7); g.lineWidth = lerp(.5, 2.2, v) * u; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - .5) * l, y - l * (.4 + r())); g.stroke(); }
  const fg = g.createLinearGradient(0, horizon - 30, 0, horizon + 260 * u); fg.addColorStop(0, rgb(fog, fogA)); fg.addColorStop(1, rgb(fog, 0)); g.fillStyle = fg; g.fillRect(0, horizon - 30, c.width, 300 * u);
  return c;
}
function ridge(seed, col, y, amp, rough, w = W * 1.5) {
  const c = mk(w, H), g = c.getContext('2d'), r = R(seed); g.fillStyle = rgb(col); g.beginPath(); g.moveTo(0, H);
  let v = 0; for (let x = 0; x <= w; x += 12 * u) { v += (r() - .5) * rough; v *= .96; g.lineTo(x, y - amp * (.5 + .5 * Math.sin(x / w * 5 + seed)) + v * amp * .2); }
  g.lineTo(w, H); g.fill(); return c;
}

// ── Karakter (arkadan; kadrodaki konu kişisinin renkleri) ─────────────
const subj = (PR.cast && (PR.cast.subject || Object.values(PR.cast).find(c => c !== PR.cast.narrator))) || {};
const LOOK = { jacket: mix(hex(subj.shirt) || [46, 58, 43], DEEP, .35), pack: [70, 74, 76], pants: [30, 32, 36], boot: [24, 20, 17], hair: hex(subj.hairColor) || [26, 20, 16], skin: hex(subj.skin) || [150, 118, 98] };
if (subj.hair === 'none') LOOK.hair = mix(LOOK.skin, BLACK, .3);
const shade = (c, k) => rgb(mix(c, BLACK, 1 - k));
function person(x, y, h, ph, { light = .5, walk = 0, head = 0, side = 1, rim = [220, 200, 160], shake = 0, t = 0, pack = true } = {}) {
  const s = h / 100, sw = Math.sin(ph) * walk, bob = -Math.abs(Math.cos(ph)) * 1.4 * walk, k = .35 + .65 * light;
  ctx.save(); ctx.translate(x + (shake ? noise(t * 30, 3) * shake * u : 0), y);
  ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.beginPath(); ctx.ellipse(0, 0, 22 * s, 4 * s, 0, 0, TAU); ctx.fill();
  ctx.scale(s, s); ctx.translate(0, bob); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  for (const [sd, v] of [[-1, sw], [1, -sw]]) {
    const lift = Math.max(0, v) * 6, hip = [sd * 5.5, -46], knee = [sd * 6.5 + v * .8, -24 - lift * .8], foot = [sd * 7 + v, -lift];
    ctx.strokeStyle = shade(LOOK.pants, k * (sd === side ? 1 : .8)); ctx.lineWidth = 10.5; ctx.beginPath(); ctx.moveTo(...hip); ctx.lineTo(...knee); ctx.stroke();
    ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(...knee); ctx.lineTo(foot[0], foot[1] - 4); ctx.stroke();
    ctx.fillStyle = shade(LOOK.boot, k); ctx.beginPath(); ctx.roundRect(foot[0] - 5.5, foot[1] - 7, 11, 8, 3); ctx.fill();
  }
  const jg = ctx.createLinearGradient(-17, 0, 17, 0); jg.addColorStop(0, shade(LOOK.jacket, k * (side < 0 ? 1.1 : .55))); jg.addColorStop(1, shade(LOOK.jacket, k * (side > 0 ? 1.1 : .55)));
  ctx.fillStyle = jg; ctx.beginPath(); ctx.moveTo(-15, -80); ctx.quadraticCurveTo(0, -84, 15, -80); ctx.lineTo(16.5, -44); ctx.quadraticCurveTo(0, -41, -16.5, -44); ctx.closePath(); ctx.fill();
  const swing = Math.sin(ph) * 4 * walk;
  for (const sd of [-1, 1]) {
    const el = [sd * 18.5, -62 - sd * swing * .25], hd = [sd * (17.5 + sd * swing * .15), -48 + Math.abs(swing) * .4];
    ctx.strokeStyle = shade(LOOK.jacket, k * (sd === side ? 1 : .6)); ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(sd * 15, -77); ctx.lineTo(...el); ctx.lineTo(...hd); ctx.stroke();
    ctx.fillStyle = shade(LOOK.skin, k * .55); ctx.beginPath(); ctx.arc(hd[0], hd[1] + 2.5, 2.8, 0, TAU); ctx.fill();
  }
  ctx.fillStyle = shade(LOOK.jacket, k * .8); ctx.beginPath(); ctx.moveTo(-9, -80); ctx.quadraticCurveTo(0, -90, 9, -80); ctx.quadraticCurveTo(0, -77, -9, -80); ctx.fill();
  if (pack) {
    const pg = ctx.createLinearGradient(0, -82, 0, -50); pg.addColorStop(0, shade(LOOK.pack, k)); pg.addColorStop(1, shade(LOOK.pack, k * .55));
    ctx.fillStyle = pg; ctx.beginPath(); ctx.roundRect(-11.5, -80, 23, 31, 5); ctx.fill();
    ctx.strokeStyle = shade(LOOK.pack, k * .4); ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(-9, -80); ctx.lineTo(-13, -70); ctx.moveTo(9, -80); ctx.lineTo(13, -70); ctx.stroke();
  }
  ctx.save(); ctx.translate(head * 1.2, 0);
  ctx.fillStyle = shade(LOOK.skin, k * .6); ctx.beginPath(); ctx.roundRect(-3.5, -86, 7, 6, 2); ctx.fill();
  for (const sd of [-1, 1]) { ctx.beginPath(); ctx.ellipse(sd * 6.1 + head * .8, -90.5, 1.4, 2.3, 0, 0, TAU); ctx.fill(); }
  ctx.fillStyle = shade(LOOK.hair, k); ctx.beginPath(); ctx.ellipse(head * .5, -91.5, 6.1, 7.4, 0, 0, TAU); ctx.fill();
  ctx.restore();
  ctx.strokeStyle = rgb(rim, .35 * light); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(side * 15, -80); ctx.lineTo(side * 16.5, -45); ctx.stroke();
  ctx.restore();
}
function shadowFigure(x, y, h, col, a) {
  if (a <= 0) return; const s = h / 100;
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha = a; ctx.fillStyle = ctx.strokeStyle = rgb(col); ctx.lineCap = 'round';
  ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-5, -46); ctx.lineTo(-6, -2); ctx.moveTo(5, -46); ctx.lineTo(6, -2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-15, -80); ctx.quadraticCurveTo(0, -84, 15, -80); ctx.lineTo(16, -44); ctx.lineTo(-16, -44); ctx.closePath(); ctx.fill();
  ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-15, -77); ctx.lineTo(-18, -48); ctx.moveTo(15, -77); ctx.lineTo(18, -48); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(0, -92, 7.6, 9, 0, 0, TAU); ctx.fill(); ctx.fillRect(-3.5, -86, 7, 7); ctx.restore();
}
function cone(x0, y0, ang, len, spread, a, col = [235, 230, 210]) {
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createLinearGradient(x0, y0, x0 + Math.cos(ang) * len, y0 + Math.sin(ang) * len); g.addColorStop(0, rgb(col, .3 * a)); g.addColorStop(.5, rgb(col, .1 * a)); g.addColorStop(1, rgb(col, 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + Math.cos(ang - spread) * len, y0 + Math.sin(ang - spread) * len); ctx.lineTo(x0 + Math.cos(ang + spread) * len, y0 + Math.sin(ang + spread) * len); ctx.closePath(); ctx.fill();
  const hg = ctx.createRadialGradient(x0, y0, 0, x0, y0, 26 * u); hg.addColorStop(0, rgb(col, .9 * a)); hg.addColorStop(1, rgb(col, 0)); ctx.fillStyle = hg; ctx.fillRect(x0 - 26 * u, y0 - 26 * u, 52 * u, 52 * u);
  ctx.restore();
}
function glow(x, y, r, col, a) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgb(col, a)); g.addColorStop(1, rgb(col, 0)); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); ctx.restore(); }

// ── Ortamlar ──────────────────────────────────────────────────────────
// Her ortam: build() önceden hazırlanan katmanlar, draw(t, sc, cam) → { spot: [x,y,ölçek], fg() }
const FOG = { forest: [118, 132, 124], night: [30, 40, 48], sea: [62, 76, 86], sky: [44, 54, 70], snow: [150, 160, 168], desert: [112, 98, 80], cave: [38, 34, 30], street: [36, 42, 50], room: [40, 44, 46], office: [44, 42, 38], lab: [50, 62, 64], plain: [26, 30, 32] };
const L = {};
const ENV = {
  forest: {
    build() { L.forest = forestSet(SEED % 997, FOG.forest); L.forestG = groundPath({ col: mix(DEEP, FOG.forest, .45), pathCol: [92, 90, 80], fog: FOG.forest, fogA: .75 }); },
    draw(t, sc, cam) {
      const f = FOG.forest; ctx.fillStyle = rgb(mix(DEEP, f, .9)); ctx.fillRect(0, 0, W, H);
      const sk = ctx.createLinearGradient(0, 0, 0, VY); sk.addColorStop(0, rgb(mix(DEEP, f, .55))); sk.addColorStop(1, rgb(mix(DEEP, f, .95))); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, VY);
      const [a, b, c, d, e, g] = L.forest;
      drawLayer(a.c, a.d, cam); fogFill(f, .35); drawLayer(b.c, b.d, cam); drift(f, t, { y: VY - 40 * u, a: .8, seed: 2 }); fogFill(f, .22);
      drawLayer(L.forestG, 4.5, cam); drawLayer(c.c, c.d, cam); drift(f, t, { y: VY + 90 * u, a: .9, seed: 5, speed: 20 });
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; for (let i = 0; i < 4; i++) { const x = W * (.25 + i * .18) + Math.sin(t * .3 + i) * 20 * u, gg = ctx.createLinearGradient(x, 0, x - 200 * u, H * .7); gg.addColorStop(0, 'rgba(190,205,195,.07)'); gg.addColorStop(1, 'rgba(190,205,195,0)'); ctx.fillStyle = gg; ctx.beginPath(); ctx.moveTo(x - 20 * u, 0); ctx.lineTo(x + 30 * u, 0); ctx.lineTo(x - 140 * u, H * .75); ctx.lineTo(x - 260 * u, H * .75); ctx.fill(); } ctx.restore();
      return { spot: proj(W / 2, VY + 120 * u, 3.6, cam), fg() { drawLayer(d.c, d.d, cam); drawLayer(e.c, e.d, cam); drift(f, t, { y: VY + 380 * u, a: .6, seed: 9, speed: 28, scale: 1.4 }); drawLayer(g.c, g.d, cam); } };
    },
  },
  night: {
    build() { L.night = forestSet(SEED % 991 + 40, [30, 40, 48], [.95, .8, .6, .45, .25, .08]); L.nightG = groundPath({ col: mix(BLACK, FOG.night, .4), pathCol: [34, 38, 40], fog: FOG.night, fogA: .5, w0: 240 * u }); },
    draw(t, sc, cam) {
      const f = FOG.night; ctx.fillStyle = rgb(mix(BLACK, f, .7)); ctx.fillRect(0, 0, W, H);
      const sk = ctx.createLinearGradient(0, 0, 0, VY); sk.addColorStop(0, '#05070b'); sk.addColorStop(1, rgb(f)); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, VY);
      for (let i = 0; i < 90; i++) { ctx.fillStyle = `rgba(220,226,240,${(.2 + .6 * hash(i + 9)) * (.6 + .4 * Math.sin(t * 2 + i))})`; ctx.fillRect(hash(i) * W, hash(i + 50) * H * .3, 2, 2); }
      glow(W * .74, H * .1, 260 * u, [200, 210, 225], .18); ctx.fillStyle = '#d8d6ca'; ctx.beginPath(); ctx.arc(W * .74, H * .1, 34 * u, 0, TAU); ctx.fill();
      const [a, b, c, d, e, g] = L.night;
      drawLayer(a.c, a.d, cam); fogFill(f, .3); drawLayer(b.c, b.d, cam); drift(f, t, { y: VY, a: 1, seed: 21 });
      drawLayer(L.nightG, 4.2, cam); drawLayer(c.c, c.d, cam);
      return { spot: proj(W / 2, VY + 140 * u, 3.6, cam), fg() { drawLayer(d.c, d.d, cam); drift(f, t, { y: VY + 300 * u, a: .8, seed: 25, speed: 22, scale: 1.3 }); drawLayer(e.c, e.d, cam); drawLayer(g.c, g.d, cam); } };
    },
  },
  sea: {
    build() { L.cliff = (() => { const c = mk(W * .7, H), g = c.getContext('2d'), r = R(SEED + 3); g.fillStyle = '#07090b'; g.beginPath(); g.moveTo(0, H); g.lineTo(0, H * .55); let y = H * .55; for (let x = 0; x <= c.width; x += 18 * u) { y += (r() - .35) * 26 * u; g.lineTo(x, Math.min(H * .86, y)); } g.lineTo(c.width, H); g.fill(); return c; })(); },
    draw(t, sc, cam) {
      const f = FOG.sea, hz = H * .5;
      const sk = ctx.createLinearGradient(0, 0, 0, hz); sk.addColorStop(0, '#06090d'); sk.addColorStop(1, rgb(f)); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, hz);
      glow(W * .62, H * .2, 300 * u, [200, 210, 225], .2); ctx.fillStyle = '#d6d4c8'; ctx.beginPath(); ctx.arc(W * .62 - cam.x * .1, H * .2, 30 * u, 0, TAU); ctx.fill();
      drift(f, t, { y: H * .18, a: .9, seed: 31, speed: 8 });
      const sg = ctx.createLinearGradient(0, hz, 0, H); sg.addColorStop(0, rgb(mix(f, BLACK, .3))); sg.addColorStop(1, '#030507'); ctx.fillStyle = sg; ctx.fillRect(0, hz, W, H - hz);
      ctx.lineWidth = 2 * u;
      for (let k = 0; k < 46; k++) {
        const q = k / 46, y = hz + Math.pow(q, 1.9) * (H - hz) * 1.02, amp = lerp(1, 22, q) * u, len = lerp(30, 260, q) * u;
        ctx.strokeStyle = `rgba(150,165,175,${lerp(.05, .14, q)})`; ctx.beginPath();
        for (let x = -20; x <= W + 20; x += 16 * u) ctx.lineTo(x, y + Math.sin(x / len + t * (1.2 + q) + k * 1.7) * amp);
        ctx.stroke();
      }
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 70; i++) { const q = hash(i * 3.3), y = hz + Math.pow(q, 1.6) * (H - hz), w = lerp(6, 90, q) * u, x = W * .62 + (hash(i * 7.1) - .5) * lerp(30, 340, q) * u + Math.sin(t * 2 + i) * 10 * u; ctx.fillStyle = `rgba(220,225,230,${(.05 + .15 * hash(i)) * (.5 + .5 * Math.sin(t * 3 + i * 2))})`; ctx.fillRect(x, y, w, 2 * u); }
      ctx.restore();
      fogFill(f, .25, hz - 80 * u, hz + 120 * u, 0);
      return { spot: [W * .55, hz + 6 * u, .9], hz, fg() { ctx.drawImage(L.cliff, -60 * u - cam.x * .4, 0); drift(f, t, { y: H * .72, a: .6, seed: 35, speed: 18, scale: 1.5 }); } };
    },
  },
  sky: {
    build() { L.clouds = [0, 1, 2].map(i => { const c = mk(W * 1.6, H * .5), g = c.getContext('2d'), r = R(SEED + 60 + i); g.filter = `blur(${(18 - i * 4) * u}px)`; for (let k = 0; k < 40; k++) { g.fillStyle = `rgba(${70 + i * 30},${80 + i * 30},${100 + i * 28},${.2 + r() * .3})`; g.beginPath(); g.ellipse(r() * c.width, c.height * (.3 + r() * .4), (80 + r() * 260) * u, (30 + r() * 70) * u, 0, 0, TAU); g.fill(); } return c; }); },
    draw(t, sc, cam) {
      const sk = ctx.createLinearGradient(0, 0, 0, H); sk.addColorStop(0, '#04060b'); sk.addColorStop(.6, '#141c2a'); sk.addColorStop(1, '#0a0e15'); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 140; i++) { ctx.fillStyle = `rgba(220,226,240,${(.2 + .6 * hash(i + 9)) * (.6 + .4 * Math.sin(t * 2 + i))})`; ctx.fillRect(hash(i) * W, hash(i + 50) * H * .6, 2, 2); }
      glow(W * .3, H * .16, 280 * u, [190, 200, 220], .16);
      L.clouds.forEach((c, i) => { const y = H * (.28 + i * .2), x = -((t * (12 + i * 16) * u + i * 300) % (c.width - W)); ctx.drawImage(c, x - cam.x * (i + 1) * .2, y); });
      return { spot: [W * .52, H * .36, 1.1], fg() { drift([60, 70, 90], t, { y: H * .82, a: .8, seed: 41, speed: 30, scale: 1.6 }); } };
    },
  },
  snow: {
    build() { L.snow = [[.32, 110, '#9aa3ab', 1.6], [.38, 160, '#7b858e', 1.3], [.46, 120, '#58616a', 1.1]].map(([y, a, c], i) => ({ d: [5, 3.2, 2][i], c: ridge(SEED + i * 7, hex(c), H * y, a * u, 2) })); L.snowG = (() => { const c = mk(W * 1.5, H), g = c.getContext('2d'), gg = g.createLinearGradient(0, H * .5, 0, H); gg.addColorStop(0, '#b8c0c6'); gg.addColorStop(1, '#6d767d'); g.fillStyle = gg; g.fillRect(0, H * .5, c.width, H); const r = R(9); for (let i = 0; i < 300; i++) { g.fillStyle = `rgba(60,70,80,${.05 + r() * .1})`; g.beginPath(); g.ellipse(r() * c.width, H * (.52 + r() * .48), (10 + r() * 80) * u, (2 + r() * 8) * u, 0, 0, TAU); g.fill(); } return c; })(); },
    draw(t, sc, cam) {
      const sk = ctx.createLinearGradient(0, 0, 0, H * .5); sk.addColorStop(0, '#3b434b'); sk.addColorStop(1, '#a9b1b8'); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, H);
      L.snow.forEach(l => { drawLayer(l.c, l.d, cam); fogFill(FOG.snow, .18); });
      drawLayer(L.snowG, 1.8, cam); drift([200, 206, 212], t, { y: H * .5, a: .8, seed: 51, speed: 34 });
      return { spot: proj(W / 2, H * .6, 1.8, cam), fg() { for (let i = 0; i < 160; i++) { const p = (hash(i) + t * (.08 + hash(i + 3) * .1)) % 1, x = (hash(i * 5) * W + t * 60 * u * (1 + hash(i)) + Math.sin(t + i) * 20 * u) % W, r = (1 + hash(i * 2) * 3) * u; ctx.fillStyle = `rgba(240,244,248,${.5 + .4 * hash(i * 9)})`; ctx.beginPath(); ctx.arc(x, p * H, r, 0, TAU); ctx.fill(); } fogFill([20, 24, 28], .15); } };
    },
  },
  desert: {
    build() { L.dunes = [[.5, 70, [120, 96, 72]], [.58, 110, [92, 72, 54]], [.7, 140, [60, 46, 34]]].map(([y, a, c], i) => ({ d: [5, 3, 1.8][i], c: (() => { const cc = mk(W * 1.5, H), g = cc.getContext('2d'); g.fillStyle = rgb(c); g.beginPath(); g.moveTo(0, H); for (let x = 0; x <= cc.width; x += 10 * u) g.lineTo(x, H * y - a * u * (.5 + .5 * Math.sin(x / (300 * u) + i * 2)) - a * u * .3 * Math.sin(x / (90 * u) + i)); g.lineTo(cc.width, H); g.fill(); return cc; })() })); },
    draw(t, sc, cam) {
      const sk = ctx.createLinearGradient(0, 0, 0, H * .55); sk.addColorStop(0, '#120f12'); sk.addColorStop(.7, '#5a4436'); sk.addColorStop(1, '#a07250'); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, H);
      glow(W * .5, H * .5, 520 * u, [240, 170, 110], .25);
      L.dunes.forEach(l => drawLayer(l.c, l.d, cam));
      drift([150, 120, 90], t, { y: H * .55, a: .6, seed: 61, speed: 40 });
      return { spot: proj(W / 2, H * .6, 2.5, cam), fg() { for (let i = 0; i < 90; i++) { const x = (hash(i) * W + t * 220 * u * (1 + hash(i + 1))) % W, y = H * (.62 + hash(i * 3) * .38); ctx.fillStyle = 'rgba(200,170,130,.25)'; ctx.fillRect(x, y, 14 * u, 1.5 * u); } fogFill([0, 0, 0], .2); } };
    },
  },
  cave: {
    build() {},
    draw(t, sc, cam) {
      ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, W, H);
      const rp = pat('rock', '#5a524a', 91, 900, [14, 50]), tr = t * .5 + (sc.i || 0) * 3;
      for (let j = 14; j >= 0; j--) {
        const z = j + 1 - (tr % 1); if (z < .3) continue;
        const id = Math.floor(tr) + j, cx = W / 2 + noise(id * .3, 1) * 140 / z * u - cam.x / z, cy = VY + noise(id * .3, 2) * 40 / z * u, rx = 330 * u / z, ry = 560 * u / z, fl = VY + 420 * u / z;
        ctx.beginPath(); ctx.rect(-80, -80, W + 160, H + 160);
        for (let i = 0; i < 40; i++) { const a = i / 40 * TAU, f = 1 + .08 * Math.sin(a * 3 + id) + .05 * Math.sin(a * 7 + id * 2); let px = cx + Math.cos(a) * rx * f, py = cy + Math.sin(a) * ry * f; if (py > fl) py = fl; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
        ctx.closePath(); rp.setTransform(new DOMMatrix().translate(cx, cy).scale(Math.min(6, 1.3 / z))); ctx.fillStyle = rp; ctx.fill('evenodd');
        ctx.fillStyle = `rgba(4,3,3,${clamp(1 - (3 + 34 * Math.exp(-z * .42)) / 44)})`; ctx.fill('evenodd');
      }
      const tx = W / 2 + Math.sin(t * .7) * 80 * u, ty = H * .46;
      const g = ctx.createRadialGradient(tx, ty, 60 * u, tx, ty, 520 * u); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.92)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      glow(tx, ty, 300 * u, [255, 214, 160], .12);
      return { spot: [W / 2, VY + 300 * u, 1], fg() {} };
    },
  },
  street: {
    build() {
      L.street = (() => { const c = mk(W * 1.4, H), g = c.getContext('2d'), r = R(SEED + 80), cx = c.width / 2;
        for (const sd of [-1, 1]) for (let k = 0; k < 9; k++) { const q = k / 9, x0 = cx + sd * lerp(60, 700, Math.pow(1 - q, 1.6)) * u, w = lerp(30, 300, Math.pow(1 - q, 1.8)) * u, top = VY - lerp(80, 900, Math.pow(1 - q, 1.5)) * u * (.7 + r() * .5), bot = VY + lerp(10, 600, Math.pow(1 - q, 2)) * u;
          g.fillStyle = rgb(mix([6, 8, 10], [40, 46, 54], q * .8)); g.fillRect(sd < 0 ? x0 - w : x0, top, w, bot - top);
          for (let i = 0; i < 26; i++) if (r() > .86) { g.fillStyle = `rgba(${200 + r() * 55},${160 + r() * 50},${90 + r() * 40},${.35 + r() * .4})`; g.fillRect((sd < 0 ? x0 - w : x0) + r() * w * .8, top + r() * (bot - top) * .8, w * .08, (bot - top) * .03); } }
        const rg = g.createLinearGradient(0, VY, 0, H); rg.addColorStop(0, '#181c22'); rg.addColorStop(1, '#07090b'); g.fillStyle = rg; g.beginPath(); g.moveTo(cx - 40 * u, VY); g.lineTo(cx + 40 * u, VY); g.lineTo(cx + 900 * u, H); g.lineTo(cx - 900 * u, H); g.fill(); return c; })();
    },
    draw(t, sc, cam) {
      const sk = ctx.createLinearGradient(0, 0, 0, VY); sk.addColorStop(0, '#05070a'); sk.addColorStop(1, '#202833'); ctx.fillStyle = sk; ctx.fillRect(0, 0, W, H);
      drawLayer(L.street, 2.4, cam);
      for (let k = 0; k < 5; k++) { const q = k / 5, [x, y, s] = proj(W / 2 + (k % 2 ? 1 : -1) * lerp(380, 60, q) * u, VY - lerp(520, 40, q) * u, 2.4, cam); const fl = .85 + .15 * (hash(Math.floor(t * 12) + k) > .93 ? 0 : 1);
        cone(x, y, Math.PI / 2, lerp(900, 120, q) * u * s, .32, .55 * fl, [255, 200, 130]); glow(x, y + lerp(900, 120, q) * u * s * .9, lerp(260, 40, q) * u, [255, 190, 120], .12 * fl); }
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; for (let i = 0; i < 40; i++) { const x = W * hash(i), y = VY + 40 * u + hash(i * 3) * (H - VY); ctx.fillStyle = `rgba(255,190,120,${.04 + .06 * hash(i * 5)})`; ctx.fillRect(x, y, 3 * u, (20 + hash(i) * 80) * u); } ctx.restore();
      drift(FOG.street, t, { y: VY + 40 * u, a: .9, seed: 81 });
      return { spot: proj(W / 2, VY + 220 * u, 2.4, cam), fg() { drift(FOG.street, t, { y: H * .82, a: .6, seed: 85, speed: 22, scale: 1.4 }); } };
    },
  },
};
// İç mekânlar: oda, ofis, laboratuvar ortak gövde
function interior(kind) {
  return {
    build() {},
    draw(t, sc, cam) {
      const f = FOG[kind], wallY = H * .64, cold = kind === 'lab';
      const wp = pat('wall' + kind, cold ? '#3a4446' : '#3b3631', 120 + kind.length, 500, [10, 26]); wp.setTransform(new DOMMatrix().translate(-cam.x * .3, 0).scale(1.6 * u));
      ctx.fillStyle = wp; ctx.fillRect(0, 0, W, wallY); ctx.fillStyle = 'rgba(0,0,0,.55)'; ctx.fillRect(0, 0, W, wallY);
      if (cold) { ctx.strokeStyle = 'rgba(0,0,0,.35)'; ctx.lineWidth = 2 * u; for (let x = 0; x < W; x += 60 * u) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, wallY); ctx.stroke(); } for (let y = 0; y < wallY; y += 60 * u) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); } }
      const fg2 = ctx.createLinearGradient(0, wallY, 0, H); fg2.addColorStop(0, cold ? '#262c2d' : '#2a221b'); fg2.addColorStop(1, '#080706'); ctx.fillStyle = fg2; ctx.fillRect(0, wallY, W, H - wallY);
      ctx.strokeStyle = 'rgba(0,0,0,.45)'; ctx.lineWidth = 2 * u; for (let k = -8; k <= 8; k++) { ctx.beginPath(); ctx.moveTo(W / 2 + k * 40 * u - cam.x * .3, wallY); ctx.lineTo(W / 2 + k * 260 * u - cam.x * .6, H); ctx.stroke(); }
      // pencere ve ay ışığı
      const wx = W * .22 - cam.x * .3, wy = H * .2, ww = 220 * u, wh = 330 * u;
      ctx.fillStyle = '#5d6a78'; ctx.fillRect(wx, wy, ww, wh); ctx.fillStyle = '#0d1014'; ctx.fillRect(wx + ww / 2 - 4 * u, wy, 8 * u, wh); ctx.fillRect(wx, wy + wh / 2 - 4 * u, ww, 8 * u);
      if (kind === 'office') { ctx.fillStyle = 'rgba(10,10,12,.85)'; for (let k = 0; k < 14; k++) ctx.fillRect(wx, wy + k * wh / 14, ww, wh / 28); }
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; const lg = ctx.createLinearGradient(wx, wy, wx + 400 * u, H); lg.addColorStop(0, 'rgba(150,170,195,.16)'); lg.addColorStop(1, 'rgba(150,170,195,0)'); ctx.fillStyle = lg; ctx.beginPath(); ctx.moveTo(wx, wy); ctx.lineTo(wx + ww, wy); ctx.lineTo(wx + ww + 520 * u, H); ctx.lineTo(wx + 260 * u, H); ctx.fill(); ctx.restore();
      if (cold) { const fl = hash(Math.floor(t * 9)) > .9 ? .35 : 1; ctx.fillStyle = `rgba(210,240,235,${.85 * fl})`; ctx.fillRect(W * .35, H * .05, W * .4, 14 * u); glow(W * .55, H * .06, 600 * u, [180, 230, 225], .18 * fl); }
      if (kind === 'office') { const lx = W * .72 - cam.x * .5, ly = H * .62; ctx.fillStyle = '#0b0a09'; ctx.fillRect(W * .38 - cam.x * .5, ly, W * .7, 30 * u); ctx.fillRect(W * .42 - cam.x * .5, ly, 18 * u, 330 * u); ctx.fillRect(W * 1.02 - cam.x * .5, ly, 18 * u, 330 * u); ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(lx - 30 * u, ly - 160 * u); ctx.lineTo(lx + 40 * u, ly - 200 * u); ctx.lineWidth = 8 * u; ctx.strokeStyle = '#0b0a09'; ctx.stroke(); cone(lx + 40 * u, ly - 200 * u, Math.PI * .6, 280 * u, .5, .9, [255, 205, 140]); glow(lx, ly, 260 * u, [255, 200, 140], .22); for (let k = 0; k < 4; k++) { ctx.fillStyle = `rgba(220,210,185,${.6 - k * .1})`; ctx.save(); ctx.translate(lx - (120 + k * 30) * u, ly - 4 * u); ctx.rotate(-.06 + k * .04); ctx.fillRect(0, -6 * u, 120 * u, 8 * u); ctx.restore(); } }
      if (cold) { ctx.fillStyle = '#121617'; ctx.fillRect(W * .3 - cam.x * .5, H * .62, W * .6, 22 * u); for (let k = 0; k < 5; k++) { const x = W * (.35 + k * .1) - cam.x * .5, h2 = (60 + hash(k) * 70) * u; ctx.fillStyle = 'rgba(120,160,160,.35)'; ctx.beginPath(); ctx.roundRect(x, H * .62 - h2, 40 * u, h2, 6 * u); ctx.fill(); ctx.fillStyle = 'rgba(200,255,240,.12)'; ctx.fillRect(x + 6 * u, H * .62 - h2 + 10 * u, 6 * u, h2 - 20 * u); } }
      // toz
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; for (let i = 0; i < 70; i++) { const p = (hash(i) + t * .02 * (1 + hash(i + 2))) % 1, x = wx + p * 600 * u + hash(i * 3) * 200 * u, y = wy + hash(i * 7) * H * .7 + Math.sin(t + i) * 20 * u; ctx.fillStyle = `rgba(200,210,220,${.15 + .3 * hash(i * 5)})`; ctx.fillRect(x, y, 2 * u, 2 * u); } ctx.restore();
      return { spot: [W * .62 - cam.x * .5, wallY + 40 * u, 1.6], fg() { fogFill(f, .12); } };
    },
  };
}
ENV.room = interior('room'); ENV.office = interior('office'); ENV.lab = interior('lab');
ENV.plain = { build() {}, draw(t, sc, cam) {
  const g = ctx.createRadialGradient(W / 2, H * .45, 0, W / 2, H * .5, H * .8); g.addColorStop(0, '#2a3033'); g.addColorStop(1, '#050607'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  const sx = W / 2 + Math.sin(t * .6) * 260 * u; cone(sx, -40 * u, Math.PI / 2 + Math.sin(t * .6) * .1, H * 1.1, .2, .5, [210, 220, 225]);
  drift(FOG.plain.map(v => v * 3), t, { y: H * .5, a: .6, seed: 91 }); drift(FOG.plain.map(v => v * 3), t, { y: H * .8, a: .5, seed: 95, speed: 22, scale: 1.4 });
  return { spot: [W / 2, H * .72, 1.4], fg() {} };
} };

// ── Objeler (sahne içine) ────────────────────────────────────────────
function prop(name, [x, y, s], t, sc) {
  const S = s * u, dark = '#050607';
  ctx.save(); ctx.translate(x, y); ctx.scale(S, S); ctx.fillStyle = dark; ctx.strokeStyle = dark; ctx.lineCap = 'round';
  switch (name) {
    case 'lighthouse': {
      ctx.translate(-260, 0); ctx.beginPath(); ctx.moveTo(-28, 0); ctx.lineTo(-18, -300); ctx.lineTo(18, -300); ctx.lineTo(28, 0); ctx.fill(); ctx.fillRect(-26, -330, 52, 30); ctx.beginPath(); ctx.moveTo(-30, -330); ctx.lineTo(0, -360); ctx.lineTo(30, -330); ctx.fill();
      ctx.restore(); const a = t * 1.3, lx = x - 260 * S, ly = y - 316 * S; cone(lx, ly, a % TAU, 1600 * u, .07, .9 * Math.max(.15, Math.abs(Math.cos(a))), [255, 236, 190]); glow(lx, ly, 60 * u, [255, 240, 200], .9); return;
    }
    case 'ship': { const b = Math.sin(t * 1.2) * 3; ctx.translate(0, b); ctx.beginPath(); ctx.moveTo(-160, -20); ctx.lineTo(160, -20); ctx.lineTo(130, 10); ctx.lineTo(-140, 10); ctx.fill(); ctx.fillRect(-60, -70, 110, 50); ctx.fillRect(20, -120, 16, 50); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(-100, -20); ctx.lineTo(-100, -160); ctx.moveTo(90, -20); ctx.lineTo(90, -150); ctx.stroke(); ctx.fillStyle = 'rgba(255,210,140,.8)'; ctx.fillRect(-40, -55, 8, 6); break; }
    case 'plane': { const by = Math.sin(t * .8) * 8; ctx.translate(-t * 40, by); ctx.scale(1.4, 1.4); ctx.beginPath(); ctx.ellipse(0, 0, 150, 16, 0, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.moveTo(-20, 0); ctx.lineTo(40, 0); ctx.lineTo(-60, 120); ctx.lineTo(-90, 120); ctx.fill(); ctx.beginPath(); ctx.moveTo(-20, 0); ctx.lineTo(40, 0); ctx.lineTo(-60, -110); ctx.lineTo(-90, -110); ctx.fill(); ctx.beginPath(); ctx.moveTo(110, 0); ctx.lineTo(150, -60); ctx.lineTo(160, -60); ctx.lineTo(150, 0); ctx.fill();
      const bl = Math.floor(t * 1.6) % 2; ctx.restore(); glow(x - t * 40 * S * 1.4 - 75 * S * 1.4, y + by * S - 120 * S * 1.4, 26 * u, [255, 60, 60], bl ? .9 : .1); glow(x - t * 40 * S * 1.4 - 75 * S * 1.4, y + by * S + 120 * S * 1.4, 26 * u, [80, 255, 120], bl ? .1 : .9); return; }
    case 'house': case 'car': case 'tree': case 'grave': case 'door': case 'window': case 'chair': case 'table': case 'phone': case 'radio': case 'camera': case 'box': case 'key': case 'skull': break;
    default: ctx.restore(); return;
  }
  if (name === 'house') { ctx.fillRect(-120, -160, 240, 160); ctx.beginPath(); ctx.moveTo(-140, -160); ctx.lineTo(0, -260); ctx.lineTo(140, -160); ctx.fill(); ctx.fillStyle = `rgba(255,200,120,${.6 + .3 * Math.sin(t * 2)})`; ctx.fillRect(40, -120, 34, 40); ctx.restore(); glow(x + 57 * S, y - 100 * S, 120 * u, [255, 190, 110], .25); return; }
  if (name === 'car') { ctx.beginPath(); ctx.roundRect(-150, -60, 300, 50, 12); ctx.fill(); ctx.beginPath(); ctx.roundRect(-90, -110, 170, 60, 20); ctx.fill(); ctx.beginPath(); ctx.arc(-90, -8, 26, 0, TAU); ctx.arc(90, -8, 26, 0, TAU); ctx.fill(); ctx.restore(); const on = hash(Math.floor(t * 5)) > .2 ? 1 : .2; cone(x + 150 * S, y - 40 * S, .05, 900 * u, .14, .8 * on, [255, 240, 210]); return; }
  if (name === 'tree') { ctx.lineWidth = 16; const br = (bx, by, l, a, d) => { if (!d) return; const ex = bx + Math.cos(a) * l, ey = by + Math.sin(a) * l; ctx.lineWidth = d * 3; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(ex, ey); ctx.stroke(); br(ex, ey, l * .7, a - .45, d - 1); br(ex, ey, l * .68, a + .5, d - 1); }; br(0, 0, 150, -Math.PI / 2, 6); }
  if (name === 'grave' || name === 'skull') { ctx.beginPath(); ctx.roundRect(-50, -140, 100, 140, [50, 50, 4, 4]); ctx.fill(); ctx.fillStyle = 'rgba(160,170,170,.25)'; ctx.fillRect(-4, -120, 8, 60); ctx.fillRect(-22, -102, 44, 8); }
  if (name === 'door') { ctx.fillStyle = '#0c0b0a'; ctx.fillRect(-80, -320, 160, 320); ctx.fillStyle = 'rgba(255,200,130,.85)'; ctx.fillRect(40, -320, 14 + 10 * Math.sin(t * .6), 320); ctx.restore(); cone(x + 50 * S, y - 160 * S, Math.PI * .55, 900 * u, .18, .5, [255, 200, 130]); return; }
  if (name === 'window') { ctx.fillStyle = '#5d6a78'; ctx.fillRect(-90, -300, 180, 240); ctx.fillStyle = dark; ctx.fillRect(-4, -300, 8, 240); ctx.fillRect(-90, -184, 180, 8); }
  if (name === 'chair') { ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-40, 0); ctx.lineTo(-40, -150); ctx.moveTo(40, 0); ctx.lineTo(30, -70); ctx.moveTo(-40, -70); ctx.lineTo(40, -70); ctx.moveTo(-40, -150); ctx.lineTo(10, -150); ctx.stroke(); ctx.rotate(.0); }
  if (name === 'table') { ctx.fillRect(-160, -100, 320, 16); ctx.fillRect(-150, -100, 12, 100); ctx.fillRect(138, -100, 12, 100); }
  if (name === 'phone') { ctx.beginPath(); ctx.roundRect(-30, -12, 60, 12, 3); ctx.fill(); ctx.restore(); glow(x, y - 6 * S, 160 * u, [170, 200, 255], .35 + .15 * Math.sin(t * 6)); return; }
  if (name === 'radio') { ctx.beginPath(); ctx.roundRect(-70, -90, 140, 90, 10); ctx.fill(); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(40, -90); ctx.lineTo(70, -190); ctx.stroke(); ctx.fillStyle = `rgba(255,170,80,${.5 + .4 * hash(Math.floor(t * 10))})`; ctx.fillRect(-50, -70, 60, 14); }
  if (name === 'camera') { ctx.fillRect(-6, -300, 12, 300); ctx.save(); ctx.translate(0, -300); ctx.rotate(.3 + Math.sin(t * .5) * .2); ctx.fillRect(-10, -26, 90, 40); ctx.restore(); ctx.restore(); glow(x + 30 * S, y - 312 * S, 30 * u, [255, 40, 40], Math.floor(t * 2) % 2 ? .9 : .15); return; }
  if (name === 'box') { ctx.fillRect(-70, -100, 140, 100); ctx.strokeStyle = 'rgba(160,150,130,.3)'; ctx.lineWidth = 2; ctx.strokeRect(-70, -100, 140, 100); ctx.beginPath(); ctx.moveTo(-70, -60); ctx.lineTo(70, -60); ctx.stroke(); }
  if (name === 'key') { ctx.restore(); glow(x, y - 10 * S, 50 * u, [255, 220, 150], .5 + .4 * Math.sin(t * 4)); return; }
  ctx.restore();
}

// ── Yakın planlar ────────────────────────────────────────────────────
const SEG = { 0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc', 5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg', '-': 'g' };
function digit(x, y, w, h, d, on, off) {
  const t = w * .16, segs = { a: [0, 0, 1, 0], b: [1, 0, 1, .5], c: [1, .5, 1, 1], d: [0, 1, 1, 1], e: [0, .5, 0, 1], f: [0, 0, 0, .5], g: [0, .5, 1, .5] };
  for (const [k, [x0, y0, x1, y1]] of Object.entries(segs)) {
    ctx.fillStyle = SEG[d]?.includes(k) ? on : off; const ax = x + x0 * w, ay = y + y0 * h, bx = x + x1 * w, by = y + y1 * h; ctx.beginPath();
    if (y0 === y1) { ctx.moveTo(ax + t * .6, ay); ctx.lineTo(ax + t * 1.1, ay - t / 2); ctx.lineTo(bx - t * 1.1, by - t / 2); ctx.lineTo(bx - t * .6, by); ctx.lineTo(bx - t * 1.1, by + t / 2); ctx.lineTo(ax + t * 1.1, ay + t / 2); }
    else { ctx.moveTo(ax, ay + t * .6); ctx.lineTo(ax + t / 2, ay + t * 1.1); ctx.lineTo(bx + t / 2, by - t * 1.1); ctx.lineTo(bx, by - t * .6); ctx.lineTo(bx - t / 2, by - t * 1.1); ctx.lineTo(ax - t / 2, ay + t * 1.1); }
    ctx.closePath(); ctx.fill();
  }
}
function closeWatch(t, sc) {
  const bg = ctx.createRadialGradient(W / 2, H * .45, 0, W / 2, H * .5, H * .7); bg.addColorStop(0, '#2d3533'); bg.addColorStop(1, '#070909'); ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 16; i++) glow(hash(i) * W, hash(i + 4) * H * .8, (30 + hash(i * 2) * 60) * u, [160, 180, 175], .06);
  const z = 1 + t * .015; ctx.save(); ctx.translate(W / 2, H * .47); ctx.scale(z, z); ctx.rotate(-.18); ctx.translate(-W / 2, -H * .47);
  const sk = mix(LOOK.skin, BLACK, .45), ag = ctx.createLinearGradient(0, H * .37, 0, H * .58); ag.addColorStop(0, rgb(mix(sk, BLACK, .3))); ag.addColorStop(.5, rgb(sk)); ag.addColorStop(1, rgb(mix(sk, BLACK, .5)));
  ctx.fillStyle = ag; ctx.beginPath(); ctx.roundRect(-W * .2, H * .38, W * 1.4, H * .19, 160 * u); ctx.fill();
  ctx.fillStyle = rgb(LOOK.jacket); ctx.beginPath(); ctx.roundRect(-W * .3, H * .345, W * .52, H * .27, 60 * u); ctx.fill();
  ctx.fillStyle = '#121414'; ctx.fillRect(W * .44, H * .36, 170 * u, H * .23);
  const cx = W * .44 + 85 * u, cy = H * .475, cw = 300 * u, ch = 330 * u, cg = ctx.createLinearGradient(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2); cg.addColorStop(0, '#2c3030'); cg.addColorStop(.5, '#0f1111'); cg.addColorStop(1, '#202424');
  ctx.fillStyle = cg; ctx.beginPath(); ctx.roundRect(cx - cw / 2, cy - ch / 2, cw, ch, 70 * u); ctx.fill();
  const lw = 220 * u, lh = 200 * u, lx = cx - lw / 2, ly = cy - lh / 2 + 10 * u, lg = ctx.createLinearGradient(lx, ly, lx + lw, ly + lh); lg.addColorStop(0, '#a4ad9c'); lg.addColorStop(1, '#7f8979');
  ctx.fillStyle = lg; ctx.beginPath(); ctx.roundRect(lx, ly, lw, lh, 14 * u); ctx.fill();
  const on = '#1b211c', off = 'rgba(27,33,28,.07)', m = /(\d{1,2})[:.](\d{2})/.exec(sc.label || '') || /(\d{1,2})[:.](\d{2})/.exec(sc.text || '');
  const time = m ? m[1].padStart(2, '0') + m[2] : '----';
  [...time].forEach((c, i) => digit(lx + 18 * u + i * 49 * u + (i > 1 ? 12 * u : 0), ly + 70 * u, 40 * u, 78 * u, c === '-' ? '-' : +c, on, off));
  if (Math.floor(t * 2) % 2 === 0) { ctx.fillStyle = on; ctx.fillRect(lx + lw / 2 - 4 * u, ly + 90 * u, 7 * u, 7 * u); ctx.fillRect(lx + lw / 2 - 4 * u, ly + 122 * u, 7 * u, 7 * u); }
  const lab = (sc.label && !m) ? sc.label.toUpperCase().slice(0, 12) : (PR.caseCard?.year || '');
  ctx.fillStyle = on; ctx.font = `700 ${18 * u}px Anton`; ctx.textAlign = 'left'; ctx.fillText(lab, lx + 16 * u, ly + 34 * u);
  ctx.restore();
}
function closeFootprints(t, sc) {
  const pp = pat('mud', '#3a342b', 77, 2600, [12, 22]); if (!L.prints) {
    const c = mk(W, H * 4), g = c.getContext('2d'), r = R(123); pp.setTransform(new DOMMatrix().scale(2.2 * u)); g.fillStyle = pp; g.fillRect(0, 0, c.width, c.height); g.fillStyle = 'rgba(20,18,14,.35)'; g.fillRect(0, 0, c.width, c.height);
    const boot = (x, y, sd, sc2, dp) => { g.save(); g.translate(x, y); g.rotate(sd * .08); g.scale(sc2 * u, sc2 * u); const sole = () => { g.beginPath(); g.ellipse(0, -24, 19, 30, 0, 0, TAU); g.ellipse(0, 30, 15, 18, 0, 0, TAU); }; g.fillStyle = `rgba(8,7,5,${.55 * dp})`; sole(); g.fill(); g.strokeStyle = `rgba(150,140,120,${.25 * dp})`; g.lineWidth = 2; g.save(); g.translate(-2, -2); sole(); g.stroke(); g.restore(); g.strokeStyle = `rgba(0,0,0,${.45 * dp})`; g.lineWidth = 3.5; for (let k = 0; k < 6; k++) { g.beginPath(); g.moveTo(-13, -46 + k * 8); g.lineTo(13, -44 + k * 8); g.stroke(); } g.restore(); };
    for (let i = 0; i < 26; i++) { const y = c.height - 140 * u - i * 150 * u, sd = i % 2 ? 1 : -1; boot(W * .45 + sd * 34 * u + (r() - .5) * 8 * u, y, sd, 1.6, 1); }
    L.prints = c;
  }
  const base = L.prints.height - H * 1.3 - (t * 200 * u) % (L.prints.height - H * 1.5);
  ctx.fillStyle = '#0d0c0a'; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 96; i++) { const a = i / 96, b = (i + 1) / 96, ya = H * (.22 + .78 * a), yb = H * (.22 + .78 * b), w = W * lerp(.45, 1.15, a), va = base + H * 1.1 * Math.pow(a, 1.5), vb = base + H * 1.1 * Math.pow(b, 1.5); ctx.drawImage(L.prints, 0, va, W, vb - va, (W - w) / 2, ya, w, yb - ya + 1); }
  ctx.fillStyle = '#1d2422'; ctx.fillRect(0, 0, W, H * .22); fogFill([29, 36, 34], 1, H * .22, H * .45, 0); drift([118, 132, 124], t, { y: H * .25, a: .8, seed: 71, speed: 18 });
}
function closeDocument(t, sc, kind) {
  const dp = pat('desk', '#2a1f17', 33, 700, [8, 18]); dp.setTransform(new DOMMatrix().scale(1.4 * u)); ctx.fillStyle = dp; ctx.fillRect(0, 0, W, H);
  const z = 1 + t * .03, px = Math.sin(t * .3) * 20 * u; ctx.save(); ctx.translate(W / 2 + px, H * .46); ctx.scale(z, z); ctx.rotate(-.05);
  const pw = 640 * u, ph = 860 * u; ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.fillRect(-pw / 2 + 18 * u, -ph / 2 + 24 * u, pw, ph);
  const pg = ctx.createLinearGradient(-pw / 2, -ph / 2, pw / 2, ph / 2); pg.addColorStop(0, '#d9ccb0'); pg.addColorStop(1, '#a8977a'); ctx.fillStyle = pg; ctx.fillRect(-pw / 2, -ph / 2, pw, ph);
  const r = R(SEED + (sc.i || 0));
  if (kind === 'map') { ctx.strokeStyle = 'rgba(80,60,40,.45)'; ctx.lineWidth = 2 * u; for (let k = 0; k < 9; k++) { ctx.beginPath(); for (let a = 0; a <= 1.001; a += .05) { const ang = a * TAU, rr = (60 + k * 32) * u * (1 + .15 * Math.sin(ang * 3 + k)); ctx.lineTo(Math.cos(ang) * rr * 1.2 - 60 * u, Math.sin(ang) * rr - 40 * u); } ctx.stroke(); } ctx.strokeStyle = 'rgba(160,30,30,.85)'; ctx.lineWidth = 9 * u; const p2 = sm(.6, 1.2, t); ctx.beginPath(); ctx.moveTo(100 * u, 120 * u); ctx.lineTo(100 * u + 60 * u * p2, 120 * u + 60 * u * p2); ctx.moveTo(160 * u, 120 * u); ctx.lineTo(160 * u - 60 * u * p2, 120 * u + 60 * u * p2); ctx.stroke(); }
  else { ctx.strokeStyle = 'rgba(40,32,24,.6)'; ctx.lineWidth = 2.4 * u; for (let k = 0; k < 16; k++) { const y = -ph / 2 + 150 * u + k * 42 * u, w = pw * (.5 + r() * .35); ctx.beginPath(); for (let x = 0; x < w; x += 8 * u) ctx.lineTo(-pw / 2 + 60 * u + x, y + Math.sin(x * .2 + k) * 3 * u + (r() - .5) * 3 * u); ctx.stroke(); } }
  if (sc.label) { ctx.font = `${44 * u}px Anton`; ctx.fillStyle = 'rgba(150,25,25,.8)'; ctx.textAlign = 'center'; ctx.save(); ctx.translate(120 * u, -ph / 2 + 90 * u); ctx.rotate(.12); ctx.strokeStyle = 'rgba(150,25,25,.8)'; ctx.lineWidth = 5 * u; const tw = ctx.measureText(sc.label.toUpperCase()).width; ctx.strokeRect(-tw / 2 - 16 * u, -36 * u, tw + 32 * u, 56 * u); ctx.fillText(sc.label.toUpperCase(), 0, 8 * u); ctx.restore(); }
  ctx.fillStyle = 'rgba(90,60,30,.18)'; ctx.beginPath(); ctx.arc(-160 * u, 260 * u, 70 * u, 0, TAU); ctx.fill();
  ctx.restore();
  glow(W * .7, H * .25, 700 * u, [255, 200, 140], .18); fogFill([0, 0, 0], .1);
}

// ── Sahne kompozisyonu ────────────────────────────────────────────────
const SCENES = (PR.scenes || []).map((s, i) => ({ ...s, i, text: (PR.words || []).filter(w => w.start >= s.start && w.start < s.end).map(w => w.word).join(' ') }));
function drawScene(sc, t) {
  const lt = t - sc.start, d = Math.max(.5, sc.end - sc.start), k = sc.i;
  if (sc.prop === 'clock') return closeWatch(lt, sc);
  if (sc.prop === 'footprints') return closeFootprints(lt, sc);
  if (sc.prop === 'letter' || sc.prop === 'map') return closeDocument(lt, sc, sc.prop);
  const env = ENV[sc.background] || ENV.plain;
  const mode = k % 3, p = lt / d;
  const cam = { x: mode === 1 ? lerp(-90, 90, p) * u * (k % 2 ? 1 : -1) : Math.sin(lt * .4) * 10 * u, push: mode === 2 ? .2 - p * .12 : .06 + p * .14, vx: W / 2, vy: VY };
  const r = env.draw(lt, sc, cam), inside = ['room', 'office', 'lab'].includes(sc.background), hasProp = sc.prop && sc.prop !== 'none' && sc.prop !== 'question';
  if (hasProp && inside) prop(sc.prop, r.spot, lt, sc);
  const ch = (sc.characters || []).find(c => c.role !== 'narrator');
  if (ch) {
    const walk = ch.pose === 'walk' ? 1 : 0, scared = ['scared', 'shocked'].includes(ch.expression);
    person(W * (k % 2 ? .38 : .58), H * .93, 640 * u, lt * 5.2, { walk, light: sc.background === 'night' || sc.background === 'cave' ? .3 : .55, side: k % 2 ? 1 : -1, head: ch.pose === 'shrug' ? Math.sin(lt) * 2 : 0, shake: scared ? 2.5 : 0, t: lt });
  } else if (['forest', 'night', 'street', 'snow'].includes(sc.background) && k % 2 === 0) {
    const [fx, fy, fs] = r.spot; shadowFigure(fx + 40 * u, fy, 150 * u * fs, mix(FOG[sc.background], BLACK, .7), .8 * sm(.4, 1.6, lt));
  }
  r.fg();
  if (hasProp && !inside) prop(sc.prop, r.spot, lt, sc);
}

// ── Yazı ve kanal kimliği ─────────────────────────────────────────────
const KEYS = (PR.keywords || []).map(x => String(x).toUpperCase());
function strokeText(txt, x, y, size, fill, stroke = '#000', sw = .14) {
  ctx.font = `${size}px Anton`; ctx.lineJoin = 'round'; ctx.lineWidth = size * sw; ctx.strokeStyle = stroke; ctx.strokeText(txt, x, y); ctx.fillStyle = fill; ctx.fillText(txt, x, y);
}
function captions(t) {
  const c = (PR.captions || []).find(g => t >= g.start && t < g.end + .15); if (!c) return;
  const size = 104, ws = c.words.map(w => String(w.word).toUpperCase()); ctx.font = `${size}px Anton`; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  const gap = size * .28, widths = ws.map(w => ctx.measureText(w).width); let lines = [[]], lw = [0];
  ws.forEach((w, i) => { const cur = lines.length - 1, add = widths[i] + (lines[cur].length ? gap : 0); if (lines[cur].length && lw[cur] + add > W * .8) { lines.push([i]); lw.push(widths[i]); } else { lines[cur].push(i); lw[cur] += add; } });
  const p = clamp((t - c.start) / .1), k = .9 + .1 * ease.outBack(p), y0 = H * .655 - (lines.length - 1) * size * .55;
  ctx.save(); ctx.translate(W * .47, H * .655); ctx.scale(k, k); ctx.translate(-W * .47, -H * .655);
  lines.forEach((ln, li) => { let x = W * .47 - lw[li] / 2; ln.forEach(i => { const w = c.words[i], on = t >= w.start && t < (c.words[i + 1]?.start ?? c.end + .15), key = KEYS.some(kk => ws[i].replace(/[^\w]/g, '').includes(kk.replace(/[^\w]/g, '')) && kk.length > 2); strokeText(ws[i], x, y0 + li * size * 1.1, size, on ? YEL : key ? '#ff8a5c' : '#ffffff'); x += widths[i] + gap; }); });
  ctx.restore();
}
function brand(t) {
  const D = PR.duration;
  if (PR.headline && t < 3.4) { const a = 1 - sm(2.9, 3.4, t); ctx.save(); ctx.globalAlpha = a; const g = ctx.createLinearGradient(0, 0, 0, H * .3); g.addColorStop(0, 'rgba(0,0,0,.7)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H * .3); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; let size = 112; ctx.font = `${size}px Anton`; const tw = ctx.measureText(PR.headline.toUpperCase()).width; if (tw > W * .76) size *= W * .76 / tw; strokeText(PR.headline.toUpperCase(), W * .47, H * .145, size, YEL); ctx.restore(); }
  const cc = PR.caseCard; if (cc && t > cc.start && t < cc.start + 3.6) {
    const lt = t - cc.start, a = sm(0, .25, lt) * (1 - sm(3.2, 3.6, lt)); ctx.save(); ctx.globalAlpha = a; const x = 54 * u, y = H * .2, w = W * .62, h = 210 * u;
    ctx.fillStyle = 'rgba(214,200,168,.95)'; ctx.fillRect(x, y, w, h); ctx.fillStyle = '#8f1d1d'; ctx.fillRect(x, y, w, 46 * u); ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.font = `${30 * u}px Anton`; ctx.fillStyle = '#f2e9d6'; ctx.fillText('CASE FILE', x + 20 * u, y + 24 * u);
    const lines = [cc.name, [cc.year, cc.place].filter(Boolean).join(' · ')].filter(Boolean), typed = Math.floor(lt * 28);
    let n = typed; ctx.fillStyle = '#1b1612'; lines.forEach((ln, i) => { const s = ln.slice(0, Math.max(0, n)); n -= ln.length; ctx.font = `${(i ? 28 : 38) * u}px Anton`; ctx.fillText(s.toUpperCase(), x + 20 * u, y + (86 + i * 60) * u); });
    ctx.restore();
  }
  const sub = PR.subscribeAt; if (sub && t > sub && t < sub + 2.2) { const lt = t - sub, a = sm(0, .2, lt) * (1 - sm(1.9, 2.2, lt)); ctx.save(); ctx.globalAlpha = a; const w = 420 * u * (.9 + .1 * ease.outBack(clamp(lt / .3))), h = 92 * u, x = W * .47 - w / 2, y = H * .44; ctx.fillStyle = '#e1241c'; ctx.beginPath(); ctx.roundRect(x, y, w, h, 18 * u); ctx.fill(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = `${54 * u}px Anton`; ctx.fillStyle = '#fff'; ctx.fillText('SUBSCRIBE', W * .47, y + h / 2 + 2 * u); ctx.restore(); }
  const wn = PR.watchNextAt; if (wn && t > wn) { const a = sm(wn, wn + .3, t); ctx.save(); ctx.globalAlpha = a; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; strokeText('WATCH NEXT', W * .47, H * .4, 96 * u / 1.5, '#ffffff'); ctx.fillStyle = YEL; ctx.beginPath(); const ax = W * .47, ay = H * .4 + 90 * u + Math.sin(t * 6) * 10 * u; ctx.moveTo(ax - 30 * u, ay); ctx.lineTo(ax + 30 * u, ay); ctx.lineTo(ax, ay + 34 * u); ctx.fill(); ctx.restore(); }
  if (L.logo) { ctx.save(); ctx.globalAlpha = .9; const s = 110 * u / Math.max(L.logo.width, L.logo.height); ctx.drawImage(L.logo, W - 40 * u - L.logo.width * s, 40 * u, L.logo.width * s, L.logo.height * s); ctx.restore(); }
}
function grade(t) {
  ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.fillStyle = 'rgba(70,100,110,.3)'; ctx.fillRect(0, 0, W, H); ctx.restore();
  const vg = ctx.createRadialGradient(W / 2, H * .48, H * .25, W / 2, H * .5, H * .75); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.6)'); ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .8; ctx.drawImage(L.grain[Math.floor(t * 24) % 5], 0, 0, W, H); ctx.restore();
  ctx.save(); ctx.globalAlpha = .45; ctx.drawImage(L.grain[(Math.floor(t * 24) + 2) % 5], 0, 0, W, H); ctx.restore();
}
async function render(t) {
  await ready;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  const sc = SCENES.findLast(s => t >= s.start) || SCENES[0];
  if (sc) {
    const lt = t - sc.start, punch = sc.i > 0 ? 1 + .06 * (1 - ease.outCubic(clamp(lt / .25))) : 1;
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(punch, punch); ctx.translate(-W / 2, -H / 2); drawScene(sc, t); ctx.restore();
    if (sc.i > 0 && lt < .08) { ctx.fillStyle = `rgba(255,255,255,${.12 * (1 - lt / .08)})`; ctx.fillRect(0, 0, W, H); }
  }
  grade(t);
  if (!PR.temiz) { brand(t); captions(t); }
}
const ready = (async () => {
  await Promise.all(['104px Anton', '700 40px Anton'].map(f => document.fonts.load(f)));
  L.grain = [0, 1, 2, 3, 4].map(k => { const c = mk(540, 960), g = c.getContext('2d'), d = g.createImageData(540, 960); let s = 9871 + k * 7919; for (let i = 0; i < d.data.length; i += 4) { s = (s * 1664525 + 1013904223) >>> 0; const v = s >>> 24; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 30; } g.putImageData(d, 0, 0); return c; });
  for (const b of new Set(SCENES.map(s => s.background))) (ENV[b] || ENV.plain).build();
  if (PR.logo) L.logo = await new Promise(res => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = PR.logo; });
})();
HB.boot(render, PR.duration, { fps: 30, hazir: ready });
window.MOTION_META = { width: W, height: H, duration: PR.duration, fps: 30, audio: [] };
