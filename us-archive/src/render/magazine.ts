/**
 * Builds the print-ready magazine as a single self-contained HTML document
 * (A4 pages via CSS @page). Sections are chosen by the package tier and only
 * rendered when they have real content — dynamic pagination, no empty pages.
 */
import type { RelationshipProfile } from '../profile/schema.js';
import type { Statistics } from '../stats/statistics.js';
import type { SectionId } from '../config/packages.js';
import { getPackage } from '../config/packages.js';
import { config } from '../config/index.js';
import { THEMES, type Theme } from './theme.js';
import { barChart, hourColumns, radarChart, splitDonut, esc } from './charts.js';
import { humanDate, monthLabel, num, hourLabel, WEEKDAYS } from './format.js';
import { renderFingerprintSVG } from '../fingerprint/fingerprint.js';

export interface MagazineOptions {
  theme?: 'light' | 'dark';
}

export function buildMagazineHTML(profile: RelationshipProfile, opts: MagazineOptions = {}): string {
  const theme = THEMES[opts.theme ?? 'light'];
  const stats = profile.statistics as unknown as Statistics;
  const pkg = getPackage(profile.packageId);
  const page = (inner: string, cls = '') => `<section class="page ${cls}">${inner}</section>`;

  const builders: Record<SectionId, () => string | null> = {
    cover: () => coverPage(profile, theme),
    our_numbers: () => ourNumbers(stats, theme),
    where_it_started: () => whereItStarted(profile, stats, theme),
    message_timeline: () => messageTimeline(stats, theme),
    communication: () => communication(profile, stats, theme),
    relationship_dna: () => relationshipDna(profile, theme),
    person_a: () => personProfile(profile, stats, theme, 0),
    person_b: () => personProfile(profile, stats, theme, 1),
    who_does_what: () => whoDoesWhat(profile, theme),
    emoji_language: () => emojiLanguage(profile, theme),
    dictionary: () => dictionary(profile, theme),
    inside_jokes: () => insideJokes(profile, theme),
    awards: () => awards(profile, theme),
    late_night: () => lateNight(stats, theme),
    most_active: () => mostActive(stats, theme),
    eras: () => eras(profile, theme),
    memorable: () => memorable(profile, theme),
    fun_stats: () => funStats(stats, theme),
    timeline: () => timeline(profile, theme),
    fingerprint: () => fingerprintPage(profile, theme),
    year_by_year: () => yearByYear(stats, theme),
    if_we_were: () => ifWeWere(profile, theme),
    future_letter: () => futureLetter(profile, theme),
    closing: () => closingPage(profile, theme),
  };

  const pages = pkg.sections
    .map((id) => builders[id]?.())
    .filter((html): html is string => Boolean(html))
    .map((html) => page(html))
    .join('\n');

  return document(pages, theme, profile);
}

// ---- shell ------------------------------------------------------------------

function document(pages: string, t: Theme, profile: RelationshipProfile): string {
  return `<!doctype html><html><head><meta charset="utf-8"/>
<style>
  @page { size: 210mm 297mm; margin: 0; }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  html, body { margin: 0; padding: 0; background: ${t.bg}; color: ${t.ink}; font-family: ${t.sans}; }
  .page { width: 210mm; height: 297mm; padding: 26mm 22mm; position: relative; overflow: hidden; page-break-after: always; background: ${t.bg}; }
  .page:last-child { page-break-after: auto; }
  h1,h2,h3 { font-family: ${t.serif}; font-weight: 600; margin: 0; }
  .eyebrow { font-size: 12px; letter-spacing: 3px; text-transform: uppercase; color: ${t.accent}; font-weight: 700; }
  .kicker { font-size: 13px; letter-spacing: 2px; text-transform: uppercase; color: ${t.inkSoft}; }
  .section-title { font-size: 40px; line-height: 1.05; margin: 8px 0 24px; }
  .lead { font-size: 18px; line-height: 1.6; color: ${t.ink}; max-width: 30em; }
  .soft { color: ${t.inkSoft}; }
  .hair { height: 1px; background: ${t.hair}; border: 0; margin: 22px 0; }
  .bignum { font-family: ${t.serif}; font-size: 68px; line-height: 1; }
  .footer { position: absolute; bottom: 14mm; left: 22mm; right: 22mm; display: flex; justify-content: space-between; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: ${t.inkSoft}; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
  .grid3 { display: grid; grid-template-columns: repeat(3,1fr); gap: 18px; }
  .card { background: ${t.surface}; border: 1px solid ${t.hair}; border-radius: 14px; padding: 20px; }
  .stat-num { font-family: ${t.serif}; font-size: 34px; line-height: 1; }
  .stat-label { font-size: 12px; letter-spacing: 1px; text-transform: uppercase; color: ${t.inkSoft}; margin-top: 8px; }
  .chip { display: inline-block; background: ${t.surface}; border: 1px solid ${t.hair}; border-radius: 999px; padding: 6px 14px; font-size: 13px; margin: 0 6px 8px 0; }
  .quote { font-family: ${t.serif}; font-size: 15px; line-height: 1.5; }
  .qs { font-size: 11px; color: ${t.inkSoft}; text-transform: uppercase; letter-spacing: 1px; }
  .term { font-family: ${t.serif}; font-size: 22px; }
  .award-cat { font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: ${t.accent}; }
</style></head><body>${pages}</body></html>`;
}

function footer(t: Theme, label: string): string {
  const wm = config.branding.watermark ? esc(config.branding.watermarkText) : '';
  return `<div class="footer"><span>${esc(config.branding.name)}</span><span>${esc(label)}</span><span>${wm}</span></div>`;
}

function scaled(svg: string): string {
  // Make inline SVG responsive within its column.
  return svg.replace('<svg ', '<svg style="max-width:100%;height:auto;" ');
}

// ---- pages ------------------------------------------------------------------

function coverPage(p: RelationshipProfile, t: Theme): string {
  const fp = renderFingerprintSVG(p.fingerprint, { size: 520, theme: t.id, title: '' });
  return `<div style="height:100%;display:flex;flex-direction:column;justify-content:space-between;">
    <div class="eyebrow">${esc(config.branding.name)}</div>
    <div style="text-align:center;margin-top:-20px;">
      <div style="opacity:0.9;">${scaled(fp)}</div>
    </div>
    <div>
      <h1 style="font-size:64px;line-height:1.02;">${esc(p.creativeSummary.coverTitle)}</h1>
      <p class="lead" style="margin-top:14px;">${esc(p.creativeSummary.coverSubtitle)}</p>
      <div class="soft" style="margin-top:26px;font-size:12px;letter-spacing:2px;text-transform:uppercase;">Generated ${humanDate(p.generatedAt)}</div>
    </div>
  </div>`;
}

function ourNumbers(s: Statistics, t: Theme): string {
  const cards = [
    { n: num(s.totalMessages), l: 'Messages' },
    { n: num(s.totalWords), l: 'Words' },
    { n: `${num(s.durationDays)}`, l: 'Days together' },
    { n: num(s.avgMessagesPerDay), l: 'Messages / day' },
    { n: num(s.mediaReferences + s.voiceReferences), l: 'Photos, voice & media' },
    { n: num(s.questionsAsked), l: 'Questions asked' },
  ];
  return `<div class="eyebrow">By the numbers</div>
    <h2 class="section-title">The story, counted.</h2>
    <div class="grid3">${cards.map((c) => `<div class="card"><div class="stat-num">${c.n}</div><div class="stat-label">${c.l}</div></div>`).join('')}</div>
    <hr class="hair"/>
    <p class="lead">${esc(String(num(s.totalMessages)))} messages later, this is what it looked like.</p>
    ${footer(t, 'Our Numbers')}`;
}

function whereItStarted(p: RelationshipProfile, s: Statistics, t: Theme): string {
  return `<div class="eyebrow">Where it started</div>
    <h2 class="section-title">The first message.</h2>
    <div class="grid2">
      <div><div class="stat-label">First message</div><div class="bignum" style="font-size:44px;">${humanDate(s.firstMessageDate)}</div></div>
      <div><div class="stat-label">Most recent</div><div class="bignum" style="font-size:44px;">${humanDate(s.lastMessageDate)}</div></div>
    </div>
    <hr class="hair"/>
    <p class="lead">${esc(p.communication.summary)}</p>
    ${footer(t, 'Where It Started')}`;
}

function messageTimeline(s: Statistics, t: Theme): string {
  if (!s.messagesByMonth.length) return '';
  const data = s.messagesByMonth.map((m) => ({ label: monthLabel(m.month), value: m.count }));
  const trimmed = data.length > 14 ? data.filter((_, i) => i % Math.ceil(data.length / 14) === 0) : data;
  return `<div class="eyebrow">Message timeline</div>
    <h2 class="section-title">How it ebbed and flowed.</h2>
    ${scaled(barChart(trimmed, t, { width: 640, barHeight: 20, format: (n) => num(n) }))}
    ${footer(t, 'Message Timeline')}`;
}

function communication(p: RelationshipProfile, s: Statistics, t: Theme): string {
  const a = s.perPerson[0];
  const b = s.perPerson[1];
  const donut = a && b ? splitDonut({ name: a.name, pct: a.percentage }, { name: b.name, pct: b.percentage }, t) : '';
  return `<div class="eyebrow">Our communication</div>
    <h2 class="section-title">The rhythm of us.</h2>
    <div class="grid2">
      <div>${scaled(donut)}</div>
      <div>
        <p class="lead">${esc(p.communication.summary)}</p>
        <div style="margin-top:16px;">
          <div class="stat-label">Median message length</div><div class="stat-num">${num(s.medianMessageLength)} chars</div>
        </div>
      </div>
    </div>
    <hr class="hair"/>
    ${scaled(hourColumns(s.messagesByHour, t, 640, 160))}
    <div class="soft" style="font-size:13px;margin-top:6px;">Messages by hour of day — you talk most around ${hourLabel(s.mostActiveHour)}.</div>
    ${footer(t, 'Our Communication')}`;
}

function relationshipDna(p: RelationshipProfile, t: Theme): string {
  const dna = p.relationshipDna;
  return `<div class="eyebrow">Relationship DNA</div>
    <h2 class="section-title">Your signature blend.</h2>
    <div class="soft" style="font-size:12px;margin-bottom:16px;">${esc(dna.disclaimer)}</div>
    <div style="display:flex;justify-content:center;">${scaled(radarChart(dna.dimensions, t, 460))}</div>
    ${footer(t, 'Relationship DNA')}`;
}

function personProfile(p: RelationshipProfile, s: Statistics, t: Theme, idx: number): string | null {
  const person = s.perPerson[idx];
  if (!person) return null;
  const arche = idx === 0 ? p.relationshipDna.archetypes.partnerA : p.relationshipDna.archetypes.partnerB;
  const chips = arche.map((a) => `<span class="chip">${esc(a.name)} · ${a.percentage}%</span>`).join('');
  const cards = [
    { n: num(person.messages), l: 'Messages' },
    { n: `${person.percentage}%`, l: 'Of all messages' },
    { n: num(person.emojis), l: 'Emojis' },
    { n: num(person.questions), l: 'Questions' },
  ];
  return `<div class="eyebrow">Profile</div>
    <h2 class="section-title">${esc(person.name)}</h2>
    <div style="margin-bottom:18px;">${chips}</div>
    <div class="grid2">${cards.map((c) => `<div class="card"><div class="stat-num">${c.n}</div><div class="stat-label">${c.l}</div></div>`).join('')}</div>
    ${footer(t, `${person.name}'s Profile`)}`;
}

function whoDoesWhat(p: RelationshipProfile, t: Theme): string {
  const cards = p.communication.whoCards
    .map(
      (c) => `<div class="card"><div class="stat-label">${esc(c.question)}</div>
        <div class="stat-num" style="margin-top:10px;">${esc(c.winner)}</div>
        <div style="font-family:${t.serif};font-size:30px;color:${t.accent};">${c.percentage}%</div></div>`,
    )
    .join('');
  return `<div class="eyebrow">Who does what</div>
    <h2 class="section-title">The honest scoreboard.</h2>
    <div class="grid2">${cards}</div>
    ${footer(t, 'Who Does What')}`;
}

function emojiLanguage(p: RelationshipProfile, t: Theme): string {
  if (!p.emojis.top.length) return '';
  const top = p.emojis.top.slice(0, 8);
  const row = top
    .map((e) => `<div style="text-align:center;"><div style="font-size:52px;">${e.emoji}</div><div class="soft" style="font-size:13px;">${num(e.count)}</div></div>`)
    .join('');
  return `<div class="eyebrow">Emoji language</div>
    <h2 class="section-title">Words weren't always enough.</h2>
    <div style="display:flex;gap:22px;flex-wrap:wrap;justify-content:space-between;margin:20px 0;">${row}</div>
    <hr class="hair"/>
    <p class="lead">${esc(p.emojis.interpretation)}</p>
    ${footer(t, 'Emoji Language')}`;
}

function dictionary(p: RelationshipProfile, t: Theme): string | null {
  if (!p.dictionary.length) return null;
  const entries = p.dictionary
    .slice(0, 8)
    .map((d) => `<div style="margin-bottom:18px;"><span class="term">${esc(d.term)}</span><div class="soft" style="font-size:15px;line-height:1.5;margin-top:4px;">${esc(d.definition)}</div></div>`)
    .join('');
  return `<div class="eyebrow">The couple dictionary</div>
    <h2 class="section-title">Words only you two understand.</h2>
    ${entries}
    ${footer(t, 'Our Dictionary')}`;
}

function insideJokes(p: RelationshipProfile, t: Theme): string | null {
  if (!p.insideJokes.length) return null;
  const items = p.insideJokes
    .slice(0, 6)
    .map((j) => `<div class="card" style="margin-bottom:14px;"><span class="term">${esc(j.term)}</span><div class="soft" style="font-size:15px;line-height:1.5;margin-top:4px;">${esc(j.definition)}</div></div>`)
    .join('');
  return `<div class="eyebrow">Inside jokes</div>
    <h2 class="section-title">You had to be there.</h2>
    ${items}
    ${footer(t, 'Inside Jokes')}`;
}

function awards(p: RelationshipProfile, t: Theme): string | null {
  if (!p.awards.length) return null;
  const items = p.awards
    .map((a) => `<div class="card"><div class="award-cat">${esc(a.category)}</div><div class="stat-num" style="margin:8px 0;">${esc(a.winner)}</div><div class="soft" style="font-size:14px;">${esc(a.blurb)}</div></div>`)
    .join('');
  return `<div class="eyebrow">Relationship awards</div>
    <h2 class="section-title">And the winner is…</h2>
    <div class="grid2">${items}</div>
    ${footer(t, 'Awards')}`;
}

function lateNight(s: Statistics, t: Theme): string {
  return `<div class="eyebrow">Late night</div>
    <h2 class="section-title">The 2am conversations.</h2>
    <div class="grid2">
      <div class="card"><div class="stat-num">${num(s.lateNightMessages)}</div><div class="stat-label">Messages after midnight</div></div>
      <div class="card"><div class="stat-num">${num(s.earlyMorningMessages)}</div><div class="stat-label">Early morning (5–8am)</div></div>
    </div>
    <hr class="hair"/>
    <p class="lead">Some of the best things get said when everyone else is asleep.</p>
    ${footer(t, 'Late Night')}`;
}

function mostActive(s: Statistics, t: Theme): string {
  const wd = s.messagesByWeekday.map((v, i) => ({ label: WEEKDAYS[i], value: v }));
  return `<div class="eyebrow">Most active</div>
    <h2 class="section-title">When you couldn't stop.</h2>
    <div class="grid2">
      <div class="card"><div class="stat-label">Busiest day ever</div><div class="stat-num">${s.mostActiveDay ? humanDate(s.mostActiveDay.date) : '—'}</div><div class="soft">${s.mostActiveDay ? num(s.mostActiveDay.count) + ' messages' : ''}</div></div>
      <div class="card"><div class="stat-label">Longest conversation</div><div class="stat-num">${num(s.longestSessionMessages)}</div><div class="soft">messages in one sitting</div></div>
    </div>
    <hr class="hair"/>
    ${scaled(barChart(wd, t, { width: 620, barHeight: 26, format: num }))}
    ${footer(t, 'Most Active')}`;
}

function eras(p: RelationshipProfile, t: Theme): string | null {
  if (!p.relationshipEras.length) return null;
  const items = p.relationshipEras
    .slice(0, 6)
    .map(
      (e) => `<div style="margin-bottom:18px;padding-left:16px;border-left:3px solid ${t.accent};">
        <div class="kicker">${humanDate(e.startDate)} — ${humanDate(e.endDate)}</div>
        <div class="term" style="margin:2px 0;">${esc(e.title)}</div>
        <div class="soft" style="font-size:14px;">${esc(e.description)}</div></div>`,
    )
    .join('');
  return `<div class="eyebrow">Relationship eras</div>
    <h2 class="section-title">Chapters of us.</h2>
    ${items}
    ${footer(t, 'Relationship Eras')}`;
}

function memorable(p: RelationshipProfile, t: Theme): string | null {
  if (!p.memorableMoments.length) return null;
  const items = p.memorableMoments
    .slice(0, 3)
    .map((m) => {
      const lines = m.quotes
        .map((q) => `<div style="margin:6px 0;"><span class="qs">${esc(q.sender)}</span><div class="quote">"${esc(q.text)}"</div></div>`)
        .join('');
      return `<div class="card" style="margin-bottom:16px;">${lines}</div>`;
    })
    .join('');
  return `<div class="eyebrow">Memorable moments</div>
    <h2 class="section-title">Small exchanges, kept.</h2>
    ${items}
    ${footer(t, 'Memorable Conversation')}`;
}

function funStats(s: Statistics, t: Theme): string {
  const chips = s.topWords.slice(0, 12).map((w) => `<span class="chip">${esc(w.word)} · ${num(w.count)}</span>`).join('');
  const quiet = s.longestQuietPeriod;
  return `<div class="eyebrow">Fun statistics</div>
    <h2 class="section-title">The little things.</h2>
    <div class="grid3" style="margin-bottom:18px;">
      <div class="card"><div class="stat-num">${num(s.linksShared)}</div><div class="stat-label">Links shared</div></div>
      <div class="card"><div class="stat-num">${quiet ? num(quiet.days) : '0'}</div><div class="stat-label">Longest quiet (days)</div></div>
      <div class="card"><div class="stat-num">${num(s.totalSessions)}</div><div class="stat-label">Conversations</div></div>
    </div>
    <div class="stat-label" style="margin-bottom:10px;">Your most-used words</div>
    <div>${chips}</div>
    ${footer(t, 'Fun Statistics')}`;
}

function timeline(p: RelationshipProfile, t: Theme): string | null {
  if (!p.timeline.length) return null;
  const items = p.timeline
    .map(
      (e) => `<div style="display:flex;gap:16px;margin-bottom:14px;align-items:baseline;">
        <div style="width:130px;" class="kicker">${humanDate(e.date)}</div>
        <div class="term" style="font-size:18px;">${esc(e.label)}${e.kind === 'detected' ? ' <span class="soft" style="font-size:11px;">(detected)</span>' : ''}</div></div>`,
    )
    .join('');
  return `<div class="eyebrow">Relationship timeline</div>
    <h2 class="section-title">The milestones.</h2>
    ${items}
    ${footer(t, 'Relationship Timeline')}`;
}

function fingerprintPage(p: RelationshipProfile, t: Theme): string {
  const svg = renderFingerprintSVG(p.fingerprint, { size: 560, theme: t.id, title: `${p.couple.partnerA} & ${p.couple.partnerB}` });
  return `<div class="eyebrow">Relationship fingerprint</div>
    <h2 class="section-title">One of one.</h2>
    <div style="display:flex;justify-content:center;margin:10px 0;">${scaled(svg)}</div>
    <p class="lead" style="text-align:center;margin:0 auto;">A generative artwork drawn from the shape of your conversations. No other couple has this one.</p>
    ${footer(t, 'Relationship Fingerprint')}`;
}

function yearByYear(s: Statistics, t: Theme): string | null {
  const byYear = new Map<string, number>();
  for (const m of s.messagesByMonth) {
    const y = m.month.slice(0, 4);
    byYear.set(y, (byYear.get(y) || 0) + m.count);
  }
  if (byYear.size < 2) return null;
  const data = [...byYear.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([y, c]) => ({ label: y, value: c }));
  return `<div class="eyebrow">Year by year</div>
    <h2 class="section-title">Your story, by the year.</h2>
    ${scaled(barChart(data, t, { width: 620, barHeight: 40, format: num }))}
    ${footer(t, 'Year by Year')}`;
}

function ifWeWere(p: RelationshipProfile, t: Theme): string | null {
  if (!p.creativeSummary.ifWeWere.length) return null;
  const items = p.creativeSummary.ifWeWere
    .map((x) => `<div style="margin-bottom:22px;"><div class="term">${esc(x.prompt)}</div><div class="lead">${esc(x.answer)}</div></div>`)
    .join('');
  return `<div class="eyebrow">If we were…</div>
    <h2 class="section-title">A little imagination.</h2>
    ${items}
    ${footer(t, 'If Our Relationship Were')}`;
}

function futureLetter(p: RelationshipProfile, t: Theme): string {
  return `<div class="eyebrow">A letter forward</div>
    <h2 class="section-title">To future us.</h2>
    <p class="quote" style="font-size:22px;line-height:1.6;">${esc(p.creativeSummary.futureLetter)}</p>
    ${footer(t, 'Future Letter')}`;
}

function closingPage(p: RelationshipProfile, t: Theme): string {
  return `<div style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;">
    <div class="eyebrow">${esc(config.branding.name)}</div>
    <h1 style="font-size:44px;max-width:16em;margin:20px 0;">${esc(p.creativeSummary.closingLine)}</h1>
    <div class="soft" style="font-size:13px;">${esc(p.couple.partnerA)} & ${esc(p.couple.partnerB)} · ${humanDate(p.generatedAt)}</div>
  </div>`;
}
