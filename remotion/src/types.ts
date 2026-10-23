export type Kelime = {word: string; start: number; end: number};

export type AltyaziGrubu = {start: number; end: number; words: Kelime[]};

export type Kamera = 'pushIn' | 'pullOut' | 'panLeft' | 'panRight' | 'tiltUp' | 'tiltDown' | 'dutch';

export type Gecis = 'flash' | 'glitch' | 'iris' | 'zoom';

export type Sahne = {
	// public/ altindaki dosya yolu (orn. "run/sahne_00.jpg"); null ise prosedurel arka plan
	src: string | null;
	// onceden bulaniklastirilmis arka derinlik katmani (opsiyonel)
	bg?: string | null;
	kind: 'image' | 'video';
	start: number;
	end: number;
	camera: Kamera;
	transition: Gecis;
};

export type DosyaKarti = {name: string; year: string; place: string; start: number};

export type ShortProps = {
	duration: number;
	audio: string | null;
	ambient: string | null;
	sfx: {boom: string | null; whoosh: string | null; hit: string | null};
	captions: AltyaziGrubu[];
	scenes: Sahne[];
	caseCard: DosyaKarti | null;
	headline: string;
	keywords: string[];
	logo: string | null;
	subscribeAt: number;
	watchNextAt: number;
};
