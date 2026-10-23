import type {StickmanProps} from './tipler';

// Remotion Studio onizlemesi icin ornek (gercek kosuda Python props.json verir)
const metin =
	'The lamp was still burning, but all three keepers were gone. Flannan Isles, Scotland, December 1900. The clock had stopped. One chair was knocked over. The third coat was still hanging there.';
const kelimeler = metin.split(' ').map((w, i) => ({word: w, start: i * 0.38, end: i * 0.38 + 0.34}));
const gruplar = [];
for (let i = 0; i < kelimeler.length; i += 3) {
	const g = kelimeler.slice(i, i + 3);
	gruplar.push({start: g[0].start, end: g[g.length - 1].end, words: g});
}
const sure = kelimeler[kelimeler.length - 1].end + 0.3;
const parca = sure / 5;

export const ornekStickman: StickmanProps = {
	duration: sure,
	audio: null,
	sfx: {boom: null, whoosh: null, hit: null, pop: null},
	captions: gruplar,
	words: kelimeler,
	cast: {
		narrator: {skin: '#e8b07a', shirt: '#f4f4f4', hair: 'none', hairColor: '#2b2b2b', glasses: false, mustache: false, beard: false},
		subject: {skin: '#f0a874', shirt: '#4a4a4a', hair: 'messy', hairColor: '#f2f2f2', glasses: true, mustache: true, beard: false},
	},
	scenes: [
		{start: 0, end: parca, background: 'night', prop: 'lighthouse', characters: [{role: 'narrator', expression: 'shocked', pose: 'point'}]},
		{start: parca, end: parca * 2, background: 'plain', prop: 'none', characters: [{role: 'narrator', expression: 'neutral', pose: 'idle'}, {role: 'subject', expression: 'scared', pose: 'hands_on_head'}], label: '1900'},
		{start: parca * 2, end: parca * 3, background: 'room', prop: 'clock', characters: [{role: 'subject', expression: 'thinking', pose: 'shrug'}]},
		{start: parca * 3, end: parca * 4, background: 'room', prop: 'chair', characters: [{role: 'narrator', expression: 'scared', pose: 'hands_up'}]},
		{start: parca * 4, end: sure, background: 'sea', prop: 'none', characters: [{role: 'subject', expression: 'sad', pose: 'walk'}]},
	],
	caseCard: {name: 'Flannan Isles Lighthouse', year: '1900', place: 'Outer Hebrides, Scotland', start: 3.2},
	headline: 'THE LAMP WAS LIT',
	keywords: ['1900', 'three'],
	logo: null,
	subscribeAt: sure * 0.5,
	watchNextAt: sure - 2.4,
};
