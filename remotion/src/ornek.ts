import type {ShortProps} from './types';

// Remotion Studio onizlemesi icin ornek veri (gercek kosuda Python props.json verir).
const metin =
	'The lighthouse lamp was still burning, but all three keepers were gone. Flannan Isles, Scotland, December 1900. The clock had stopped. One chair was knocked over. Two oilskin coats were missing from their hooks. The third was still hanging there.';

const kelimeler = metin.split(' ').map((w, i) => ({word: w, start: i * 0.38, end: i * 0.38 + 0.34}));
const gruplar = [];
for (let i = 0; i < kelimeler.length; i += 3) {
	const g = kelimeler.slice(i, i + 3);
	gruplar.push({start: g[0].start, end: g[g.length - 1].end, words: g});
}
const sure = kelimeler[kelimeler.length - 1].end + 0.3;
const kameralar = ['pushIn', 'panLeft', 'tiltUp', 'pullOut', 'dutch', 'panRight'] as const;
const gecisler = ['zoom', 'glitch', 'flash', 'iris'] as const;
const n = 6;

export const ornekProps: ShortProps = {
	duration: sure,
	audio: null,
	ambient: null,
	sfx: {boom: null, whoosh: null, hit: null},
	captions: gruplar,
	scenes: Array.from({length: n}, (_, i) => ({
		src: null,
		kind: 'image' as const,
		start: (sure / n) * i,
		end: (sure / n) * (i + 1),
		camera: kameralar[i % kameralar.length],
		transition: gecisler[i % gecisler.length],
	})),
	caseCard: {name: 'Flannan Isles Lighthouse', year: '1900', place: 'Outer Hebrides, Scotland', start: 3.2},
	headline: 'THE LAMP WAS LIT',
	keywords: ['1900', 'three', 'still'],
	logo: null,
	subscribeAt: sure * 0.5,
	watchNextAt: sure - 2.4,
};
