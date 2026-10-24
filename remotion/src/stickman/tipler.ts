import type {AltyaziGrubu, DosyaKarti} from '../types';

export type Ifade = 'neutral' | 'scared' | 'shocked' | 'sad' | 'thinking' | 'angry' | 'happy';
export type Poz = 'idle' | 'point' | 'hands_up' | 'hands_on_head' | 'shrug' | 'walk';
export type Sac = 'none' | 'short' | 'messy' | 'long' | 'bun' | 'cap' | 'hat';

export type Gorunum = {
	skin: string;
	shirt: string;
	hair: Sac;
	hairColor: string;
	glasses: boolean;
	mustache: boolean;
	beard: boolean;
};

export type Arkaplan =
	| 'plain'
	| 'room'
	| 'night'
	| 'forest'
	| 'sea'
	| 'sky'
	| 'office'
	| 'lab'
	| 'snow'
	| 'desert'
	| 'cave'
	| 'street';

export type Obje =
	| 'none'
	| 'door'
	| 'window'
	| 'chair'
	| 'table'
	| 'phone'
	| 'radio'
	| 'map'
	| 'letter'
	| 'clock'
	| 'car'
	| 'ship'
	| 'plane'
	| 'lighthouse'
	| 'house'
	| 'tree'
	| 'grave'
	| 'box'
	| 'key'
	| 'footprints'
	| 'camera'
	| 'skull'
	| 'question';

export type SahneKarakteri = {
	role: string; // cast icindeki anahtar (narrator, subject, other)
	expression: Ifade;
	pose: Poz;
};

export type StickSahne = {
	start: number;
	end: number;
	background: Arkaplan;
	prop: Obje;
	characters: SahneKarakteri[];
	// ekranda kucuk tabela/etiket olarak gorunen kisa yazi (orn. "1937"), opsiyonel
	label?: string;
	// Gemini'nin bu hikayeye ozel cizdigi SVG'ler (public/ altinda yol). Yoksa kodlu dekor kullanilir.
	bgSvg?: string | null;
	propSvg?: string | null;
};

export type StickmanProps = {
	duration: number;
	audio: string | null;
	sfx: {boom: string | null; whoosh: string | null; hit: string | null; pop: string | null};
	captions: AltyaziGrubu[];
	words: {word: string; start: number; end: number}[];
	cast: Record<string, Gorunum>;
	scenes: StickSahne[];
	caseCard: DosyaKarti | null;
	headline: string;
	keywords: string[];
	logo: string | null;
	subscribeAt: number;
	watchNextAt: number;
	// thumbnail icin: altyazi/manset/CTA gizli temiz kare
	temiz?: boolean;
};
