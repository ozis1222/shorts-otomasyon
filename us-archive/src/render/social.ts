/**
 * Social & wallpaper asset generation. Each asset is an HTML card screenshotted
 * by headless Chromium at an exact device size (so emoji, fonts and gradients
 * render identically to the magazine). Counts come from the package tier.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { RelationshipProfile } from '../profile/schema.js';
import type { Statistics } from '../stats/statistics.js';
import { getPackage } from '../config/packages.js';
import { config } from '../config/index.js';
import { THEMES, type Theme } from './theme.js';
import { renderFingerprintSVG } from '../fingerprint/fingerprint.js';
import { num } from './format.js';
import { esc } from './charts.js';
import { getBrowser } from './browser.js';

interface Card {
  eyebrow: string;
  headline: string;
  sub?: string;
  big?: string;
}

function cardHTML(card: Card, t: Theme, w: number, h: number, fingerprintSvg?: string): string {
  const wm = config.branding.watermark
    ? `<div style="position:absolute;bottom:${Math.round(h * 0.04)}px;left:0;right:0;text-align:center;font-size:${Math.round(w * 0.022)}px;letter-spacing:2px;text-transform:uppercase;color:${t.inkSoft};font-family:${t.sans};">${esc(config.branding.watermarkText)}</div>`
    : '';
  const art = fingerprintSvg
    ? `<div style="opacity:0.16;position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">${fingerprintSvg.replace('<svg ', `<svg style="width:${w * 1.1}px;height:auto;" `)}</div>`
    : '';
  return `<!doctype html><html><head><meta charset="utf-8"/><style>
    *{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact;}
    body{width:${w}px;height:${h}px;background:${t.bg};color:${t.ink};font-family:${t.sans};overflow:hidden;}
    .wrap{position:relative;width:100%;height:100%;padding:${Math.round(w * 0.09)}px;display:flex;flex-direction:column;justify-content:center;}
    .eyebrow{font-size:${Math.round(w * 0.028)}px;letter-spacing:4px;text-transform:uppercase;color:${t.accent};font-weight:700;margin-bottom:${Math.round(h * 0.02)}px;}
    .headline{font-family:${t.serif};font-weight:600;font-size:${Math.round(w * 0.085)}px;line-height:1.05;}
    .big{font-family:${t.serif};font-weight:600;font-size:${Math.round(w * 0.2)}px;line-height:1;color:${t.accent};margin:${Math.round(h * 0.02)}px 0;}
    .sub{font-size:${Math.round(w * 0.038)}px;color:${t.inkSoft};margin-top:${Math.round(h * 0.02)}px;line-height:1.5;}
  </style></head><body><div class="wrap">${art}<div style="position:relative;">
    <div class="eyebrow">${esc(card.eyebrow)}</div>
    ${card.big ? `<div class="big">${esc(card.big)}</div>` : ''}
    <div class="headline">${esc(card.headline)}</div>
    ${card.sub ? `<div class="sub">${esc(card.sub)}</div>` : ''}
  </div>${wm}</div></body></html>`;
}

/** Build the pool of data-backed cards; only cards with real data are emitted. */
function buildCards(p: RelationshipProfile, s: Statistics): Card[] {
  const cards: Card[] = [];
  cards.push({ eyebrow: config.branding.name, big: num(s.totalMessages), headline: 'messages later…', sub: `${p.couple.partnerA} & ${p.couple.partnerB}` });
  for (const c of p.communication.whoCards.slice(0, 4)) {
    cards.push({ eyebrow: c.question, big: `${c.percentage}%`, headline: c.winner });
  }
  if (p.emojis.top[0]) cards.push({ eyebrow: 'Our most used emoji', big: p.emojis.top[0].emoji, headline: `${num(p.emojis.top[0].count)} times`, sub: p.emojis.interpretation });
  const topDna = [...p.relationshipDna.dimensions].sort((a, b) => b.score - a.score)[0];
  if (topDna) cards.push({ eyebrow: 'Our relationship DNA', big: `${topDna.score}`, headline: topDna.name, sub: p.relationshipDna.disclaimer });
  if (p.insideJokes[0]) cards.push({ eyebrow: 'Our weirdest inside joke', headline: p.insideJokes[0].term, sub: p.insideJokes[0].definition });
  if (p.dictionary[0]) cards.push({ eyebrow: 'From our dictionary', headline: p.dictionary[0].term, sub: p.dictionary[0].definition });
  cards.push({ eyebrow: 'Late night champions', big: num(s.lateNightMessages), headline: 'messages after midnight' });
  if (s.mostActiveDay) cards.push({ eyebrow: 'Our busiest day', big: num(s.mostActiveDay.count), headline: 'messages in one day' });
  if (p.awards[0]) cards.push({ eyebrow: p.awards[0].category, headline: p.awards[0].winner, sub: p.awards[0].blurb });
  if (s.topWords[0]) cards.push({ eyebrow: 'Our most-used word', big: `“${s.topWords[0].word}”`, headline: `${num(s.topWords[0].count)} times` });
  cards.push({ eyebrow: config.branding.name, headline: p.creativeSummary.closingLine });
  return cards;
}

export interface GeneratedAsset {
  path: string;
  kind: 'story' | 'instagram' | 'phone_wallpaper' | 'desktop_wallpaper' | 'poster';
}

export async function renderSocialAssets(
  profile: RelationshipProfile,
  outDir: string,
  theme: 'light' | 'dark' = 'light',
): Promise<GeneratedAsset[]> {
  const t = THEMES[theme];
  const tDark = THEMES.dark;
  const stats = profile.statistics as unknown as Statistics;
  const pkg = getPackage(profile.packageId);
  const cards = buildCards(profile, stats);
  const assets: GeneratedAsset[] = [];

  const storiesDir = join(outDir, 'stories');
  const igDir = join(outDir, 'instagram');
  const wallDir = join(outDir, 'wallpapers');
  await Promise.all([mkdir(storiesDir, { recursive: true }), mkdir(igDir, { recursive: true }), mkdir(wallDir, { recursive: true })]);

  const browser = await getBrowser();

  const shoot = async (html: string, w: number, h: number, path: string) => {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    try {
      await page.setContent(html, { waitUntil: 'networkidle' });
      const buf = await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: w, height: h } });
      await writeFile(path, buf);
    } finally {
      await page.close();
    }
  };

  // Story cards 1080x1920.
  const fpSvg = renderFingerprintSVG(profile.fingerprint, { size: 1080, theme });
  for (let i = 0; i < pkg.assets.storyCards; i++) {
    const card = cards[i % cards.length];
    const path = join(storiesDir, `story-${String(i + 1).padStart(2, '0')}.png`);
    await shoot(cardHTML(card, t, 1080, 1920, i % 3 === 0 ? fpSvg : undefined), 1080, 1920, path);
    assets.push({ path, kind: 'story' });
  }

  // Instagram cards 1080x1350.
  for (let i = 0; i < pkg.assets.instagramCards; i++) {
    const card = cards[(i + 1) % cards.length];
    const path = join(igDir, `instagram-${String(i + 1).padStart(2, '0')}.png`);
    await shoot(cardHTML(card, t, 1080, 1350, undefined), 1080, 1350, path);
    assets.push({ path, kind: 'instagram' });
  }

  // Phone wallpapers 1080x1920 (fingerprint-forward, minimal).
  for (let i = 0; i < pkg.assets.phoneWallpapers; i++) {
    const useDark = i % 2 === 1;
    const wt = useDark ? tDark : t;
    const svg = renderFingerprintSVG(profile.fingerprint, { size: 1080, theme: useDark ? 'dark' : theme, title: `${profile.couple.partnerA} & ${profile.couple.partnerB}` });
    const html = wallpaperHTML(svg, wt, 1080, 1920);
    const path = join(wallDir, `phone-wallpaper-${i + 1}.png`);
    await shoot(html, 1080, 1920, path);
    assets.push({ path, kind: 'phone_wallpaper' });
  }

  // Desktop wallpapers 1920x1080.
  for (let i = 0; i < pkg.assets.desktopWallpapers; i++) {
    const svg = renderFingerprintSVG(profile.fingerprint, { size: 1080, theme, title: `${profile.couple.partnerA} & ${profile.couple.partnerB}` });
    const html = wallpaperHTML(svg, t, 1920, 1080);
    const path = join(wallDir, `desktop-wallpaper-${i + 1}.png`);
    await shoot(html, 1920, 1080, path);
    assets.push({ path, kind: 'desktop_wallpaper' });
  }

  // Fingerprint poster 1080x1350.
  if (pkg.assets.fingerprintPoster) {
    const svg = renderFingerprintSVG(profile.fingerprint, { size: 1000, theme, title: `${profile.couple.partnerA} & ${profile.couple.partnerB}` });
    const path = join(outDir, 'relationship-fingerprint-poster.png');
    await shoot(posterHTML(svg, t, profile), 1080, 1350, path);
    assets.push({ path, kind: 'poster' });
  }

  // Also drop the raw fingerprint SVG + a standalone PNG at the archive root.
  const rawSvg = renderFingerprintSVG(profile.fingerprint, { size: 1000, theme, title: `${profile.couple.partnerA} & ${profile.couple.partnerB}` });
  await writeFile(join(outDir, 'relationship-fingerprint.svg'), rawSvg);
  const fpPath = join(outDir, 'relationship-fingerprint.png');
  await shoot(`<!doctype html><html><body style="margin:0">${rawSvg.replace('<svg ', '<svg style="width:1000px;height:1000px" ')}</body></html>`, 1000, 1000, fpPath);
  assets.push({ path: fpPath, kind: 'poster' });

  return assets;
}

function wallpaperHTML(svg: string, t: Theme, w: number, h: number): string {
  return `<!doctype html><html><body style="margin:0;width:${w}px;height:${h}px;background:${t.bg};display:flex;align-items:center;justify-content:center;overflow:hidden;">
    <div style="width:${Math.min(w, h) * 0.9}px;">${svg.replace('<svg ', '<svg style="width:100%;height:auto;" ')}</div></body></html>`;
}

function posterHTML(svg: string, t: Theme, p: RelationshipProfile): string {
  return `<!doctype html><html><head><meta charset="utf-8"/></head>
    <body style="margin:0;width:1080px;height:1350px;background:${t.bg};color:${t.ink};font-family:${t.sans};display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px;box-sizing:border-box;">
    <div style="font-size:24px;letter-spacing:6px;text-transform:uppercase;color:${t.accent};font-weight:700;">Relationship Fingerprint</div>
    <div style="width:780px;margin:20px 0;">${svg.replace('<svg ', '<svg style="width:100%;height:auto;" ')}</div>
    <div style="font-family:${t.serif};font-size:44px;">${esc(p.couple.partnerA)} & ${esc(p.couple.partnerB)}</div>
    <div style="font-size:20px;color:${t.inkSoft};margin-top:8px;">${esc((p.statistics as any).totalMessages?.toLocaleString?.() ?? '')} messages · one of one</div>
  </body></html>`;
}
