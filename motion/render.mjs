#!/usr/bin/env node
// motion-engine render köprüsü.
// Kullanım: node motion/render.mjs <run-klasörü> <çıktı.mp4> [--still <sn> <kare.png>] [--workers N]
// <run-klasörü>/props.json Python tarafından yazılır (stickman props biçimi: duration, audio, sfx, captions, words, cast, scenes...).
// motion-engine reposu MOTION_ENGINE_DIR'de (varsayılan: <repo>/motion-engine) bulunmalı: runtime, Chromium başlatıcı ve fontları oradan gelir.
import { execFileSync } from 'node:child_process';
import { cp, mkdir, readFile, writeFile, rm, copyFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { cpus } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url)), repo = resolve(here, '..');
const ME = resolve(process.env.MOTION_ENGINE_DIR || join(repo, 'motion-engine'));
if (!existsSync(join(ME, 'engine/runtime.js')) || !existsSync(join(ME, 'lib/browser.mjs'))) throw new Error(`motion-engine bulunamadı: ${ME} (MOTION_ENGINE_DIR ayarla)`);
const { launchBrowser } = await import(pathToFileURL(join(ME, 'lib/browser.mjs')).href);

const args = process.argv.slice(2), run = resolve(args[0]), out = resolve(args[1]);
const opt = k => { const i = args.indexOf('--' + k); return i >= 0 ? args.slice(i + 1, i + 3) : null; };
const props = JSON.parse(await readFile(join(run, 'props.json'), 'utf8'));
const FPS = 30, W = 1080, H = 1920, total = Math.round(props.duration * FPS);
const sh = (c, a) => execFileSync(c, a, { encoding: 'utf8', maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'pipe'] });
const ff = a => sh(process.env.FFMPEG || 'ffmpeg', ['-v', 'error', '-y', ...a]);

// 1) motion-engine projesi
const proj = join(run, 'project');
await rm(proj, { recursive: true, force: true }); await mkdir(join(proj, 'engine'), { recursive: true });
await cp(join(ME, 'engine/runtime.js'), join(proj, 'engine/runtime.js'));
await cp(join(ME, 'assets/fonts'), join(proj, 'fonts'), { recursive: true });
await copyFile(join(repo, 'fonts/Anton-Regular.ttf'), join(proj, 'fonts/Anton-Regular.ttf'));
await copyFile(join(here, 'scene.js'), join(proj, 'scene.js'));
if (props.logo && existsSync(join(run, props.logo))) await copyFile(join(run, props.logo), join(proj, 'logo.png'));
const page = temiz => `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>short</title><style>
@font-face{font-family:Anton;src:url('./fonts/Anton-Regular.ttf') format('truetype');font-display:block}
@font-face{font-family:Manrope;src:url('./fonts/manrope-latin.woff2') format('woff2');font-weight:200 800;font-display:block}
*{box-sizing:border-box}body{margin:0;background:#000}#stage{width:var(--w);height:var(--h);position:relative;overflow:hidden}canvas{display:block;width:100%;height:100%}</style></head>
<body><main id="stage"><canvas id="film"></canvas></main><script>window.PROPS=${JSON.stringify({ ...props, logo: props.logo ? './logo.png' : null, temiz })};</script>
<script src="./engine/runtime.js"></script><script src="./scene.js"></script></body></html>`;
await writeFile(join(proj, 'index.html'), page(false));
await writeFile(join(proj, 'temiz.html'), page(true));

async function open(browser, file) {
  const p = await browser.newPage({ viewport: { width: W, height: H } }), errors = [];
  p.on('pageerror', e => errors.push(e.message));
  await p.goto(pathToFileURL(join(proj, file)).href); await p.evaluate(() => window.bannerReady);
  if (errors.length) throw new Error('Sahne hatası: ' + errors.join(' | '));
  return { p, errors };
}

// İsteğe bağlı: yazısız tek kare (thumbnail tabanı)
const still = opt('still');
if (still) {
  const b = await launchBrowser();
  try { const { p } = await open(b, 'temiz.html'); await p.evaluate(t => window.render(t), +still[0]); await p.screenshot({ path: resolve(still[1]), type: 'png' }); }
  finally { await b.close(); }
  console.log('  kare: ' + resolve(still[1]));
  if (!args.includes('--also-video')) process.exit(0);
}

// 2) Paralel kare render
const frames = join(run, 'frames'); await rm(frames, { recursive: true, force: true }); await mkdir(frames, { recursive: true });
const workers = Math.max(1, Number(opt('workers')?.[0]) || Math.min(4, cpus().length));
const t0 = Date.now(); let done = 0;
await Promise.all(Array.from({ length: workers }, async (_, w) => {
  const b = await launchBrowser();
  try {
    const { p, errors } = await open(b, 'index.html');
    for (let f = w; f < total; f += workers) {
      await p.evaluate(t => window.render(t), f / FPS);
      await p.screenshot({ path: join(frames, `f${String(f).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 92 });
      if (++done % 300 === 0) console.log(`  ${Math.round(done / total * 100)}% (${Math.round((Date.now() - t0) / 1000)} sn)`);
    }
    if (errors.length) throw new Error(errors.join(' | '));
  } finally { await b.close(); }
}));
console.log(`  ${total} kare, ${workers} işçi, ${Math.round((Date.now() - t0) / 1000)} sn`);

// 3) Ses: anlatım + sentez yatak (ambiyans, uğultu) + sahne geçişi efektleri; anlatım gelince yatak geri çekilir
const sfxDir = join(run, 'sfx');
sh('node', [join(here, 'sfx.mjs'), sfxDir, String(Math.ceil(props.duration + 2))]);
const ins = [], ch = [], fx = [];
const add = (file, at, gain, tag) => { if (!file || !existsSync(file)) return; const i = ins.length / 2; ins.push('-i', file); ch.push(`[${i}:a]aresample=48000,aformat=channel_layouts=stereo,volume=${gain}dB,adelay=${Math.round(at * 1000)}:all=1[${tag}]`); fx.push(`[${tag}]`); };
const S = props.sfx || {}, abs = p => p ? resolve(run, p) : null;
add(abs(S.boom), 0, -4, 'boom');
(props.scenes || []).forEach((s, i) => { if (i) add(abs(S.whoosh), Math.max(0, s.start - .18), -10, `w${i}`); });
if (props.caseCard) add(abs(S.hit), props.caseCard.start, -8, 'hit');
if (props.subscribeAt) add(abs(S.pop), props.subscribeAt, -10, 'pop');
add(join(sfxDir, 'low_hit.wav'), Math.max(0, props.duration - 2.2), -8, 'end');
const v = ins.length / 2; ins.push('-i', resolve(run, props.audio));
const bed = ins.length / 2; ins.push('-i', join(sfxDir, 'ambience.wav'), '-i', join(sfxDir, 'drone.wav'));
const dur = props.duration.toFixed(3);
const filter = [...ch,
  `[${v}:a]aresample=48000,aformat=channel_layouts=stereo,apad[vo]`, `[vo]asplit=2[vo1][vk]`,
  `[${bed}:a]aresample=48000,aformat=channel_layouts=stereo,volume=-17dB[amb]`, `[${bed + 1}:a]aresample=48000,aformat=channel_layouts=stereo,volume=-15dB[dr]`,
  `[amb][dr]${fx.join('')}amix=inputs=${2 + fx.length}:normalize=0[bg]`,
  `[bg][vk]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck]`,
  `[vo1][duck]amix=inputs=2:normalize=0,atrim=0:${dur},alimiter=limit=0.89,loudnorm=I=-14:TP=-1.5:LRA=11[out]`].join(';');
const mix = join(run, 'mix.wav');
ff([...ins, '-filter_complex', filter, '-map', '[out]', '-ar', '48000', mix]);

// 4) MP4
await mkdir(dirname(out), { recursive: true });
ff(['-framerate', String(FPS), '-i', join(frames, 'f%06d.jpg'), '-i', mix, '-c:v', 'libx264', '-preset', process.env.X264_PRESET || 'medium', '-b:v', process.env.VIDEO_BITRATE || '16000k',
  '-maxrate', process.env.VIDEO_BITRATE || '16000k', '-bufsize', '24000k', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
  '-c:a', 'aac', '-b:a', '192k', '-t', dur, '-movflags', '+faststart', out]);
const pr = JSON.parse(sh(process.env.FFPROBE || 'ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', out]));
const vs = pr.streams.find(s => s.codec_type === 'video');
if (vs.width !== W || vs.height !== H || Math.abs(+pr.format.duration - props.duration) > .2 || !pr.streams.some(s => s.codec_type === 'audio')) throw new Error('Çıktı doğrulanamadı: ' + JSON.stringify(pr));
await rm(frames, { recursive: true, force: true });
console.log(`  video: ${out} (${(+pr.format.duration).toFixed(2)} sn, ${W}x${H})`);
