import React from 'react';
import {random} from 'remotion';
import type {Gorunum, Ifade, Poz} from './tipler';

// Cizim dili: kalin siyah kontur, duz renkler, buyuk yuvarlak kafa, ince cubuk kol/bacak.
// Koordinatlar karakterin ayak ortasina gore (0,0); yukari negatif. Boy ~ 930 px.
export const KONTUR = '#141414';
const K = 9; // ana kontur kalinligi
const UZUV = 8; // kol/bacak kalinligi

const KAFA_Y = -760;
const KAFA_R = 158;

type Props = {
	gorunum: Gorunum;
	ifade: Ifade;
	poz: Poz;
	// 0..1 agiz acikligi (konusma)
	agiz: number;
	// karede yerel zaman (sn) -> goz kirpma, nefes, jest
	t: number;
	tohum: string;
	// saga bakiyorsa 1, sola -1 (yuz detaylari kayar)
	yon?: 1 | -1;
};

const kol = (omuzX: number, omuzY: number, dirsekX: number, dirsekY: number, elX: number, elY: number) => (
	<>
		<path
			d={`M ${omuzX} ${omuzY} Q ${dirsekX} ${dirsekY} ${elX} ${elY}`}
			stroke={KONTUR}
			strokeWidth={UZUV}
			strokeLinecap="round"
			fill="none"
		/>
	</>
);

// Poza gore el konumlari (sol el = ekranin solu)
const kollar = (poz: Poz, t: number) => {
	const sal = Math.sin(t * 2.2) * 6;
	switch (poz) {
		case 'point': {
			const s = Math.sin(t * 5) * 8;
			return [kol(-112, -565, -150, -440, -128, -330), kol(112, -565, 230, -600, 330 + s, -650 + s)];
		}
		case 'hands_up': {
			const s = Math.sin(t * 9) * 10;
			return [kol(-112, -565, -230, -680, -250 + s, -820), kol(112, -565, 230, -680, 250 - s, -820)];
		}
		case 'hands_on_head':
			return [kol(-112, -565, -260, -720, -150, -880), kol(112, -565, 260, -720, 150, -880)];
		case 'shrug': {
			const s = Math.abs(Math.sin(t * 3)) * 18;
			return [kol(-112, -565, -230, -470 - s, -270, -560 - s), kol(112, -565, 230, -470 - s, 270, -560 - s)];
		}
		case 'walk': {
			const s = Math.sin(t * 8) * 60;
			return [kol(-112, -565, -140 + s * 0.4, -440, -130 + s, -320), kol(112, -565, 140 - s * 0.4, -440, 130 - s, -320)];
		}
		case 'idle':
		default:
			return [kol(-112, -565, -150, -440 + sal, -140, -320 + sal), kol(112, -565, 150, -440 - sal, 140, -320 - sal)];
	}
};

const bacaklar = (poz: Poz, t: number) => {
	if (poz === 'walk') {
		const s = Math.sin(t * 8) * 55;
		return (
			<>
				<path d={`M -40 -290 L ${-40 + s} 0`} stroke={KONTUR} strokeWidth={UZUV} strokeLinecap="round" />
				<path d={`M 40 -290 L ${40 - s} 0`} stroke={KONTUR} strokeWidth={UZUV} strokeLinecap="round" />
			</>
		);
	}
	return (
		<>
			<path d="M -42 -290 L -52 0" stroke={KONTUR} strokeWidth={UZUV} strokeLinecap="round" />
			<path d="M 42 -290 L 52 0" stroke={KONTUR} strokeWidth={UZUV} strokeLinecap="round" />
		</>
	);
};

const Sac: React.FC<{g: Gorunum}> = ({g}) => {
	const c = g.hairColor;
	const y = KAFA_Y;
	switch (g.hair) {
		case 'messy':
			// referanstaki daginik beyaz sac: kafanin cevresinde dalgali bulut
			return (
				<path
					d={`M -150 ${y + 40} C -230 ${y - 10}, -205 ${y - 120}, -150 ${y - 135}
					    C -170 ${y - 210}, -70 ${y - 230}, -40 ${y - 175}
					    C -20 ${y - 245}, 80 ${y - 235}, 80 ${y - 175}
					    C 140 ${y - 225}, 230 ${y - 160}, 175 ${y - 100}
					    C 245 ${y - 70}, 225 ${y + 20}, 158 ${y + 45}
					    C 150 ${y - 40}, 110 ${y - 110}, 0 ${y - 118}
					    C -110 ${y - 110}, -150 ${y - 40}, -150 ${y + 40} Z`}
					fill={c}
					stroke={KONTUR}
					strokeWidth={K - 2}
					strokeLinejoin="round"
				/>
			);
		case 'short':
			return (
				<path
					d={`M -158 ${y + 5} C -165 ${y - 120}, -80 ${y - 175}, 0 ${y - 172}
					    C 90 ${y - 175}, 165 ${y - 120}, 158 ${y + 5}
					    C 130 ${y - 70}, 60 ${y - 95}, 0 ${y - 92}
					    C -70 ${y - 95}, -130 ${y - 70}, -158 ${y + 5} Z`}
					fill={c}
					stroke={KONTUR}
					strokeWidth={K - 2}
					strokeLinejoin="round"
				/>
			);
		case 'long':
			return (
				<path
					d={`M -150 ${y + 150} C -205 ${y + 20}, -190 ${y - 165}, 0 ${y - 172}
					    C 190 ${y - 165}, 205 ${y + 20}, 150 ${y + 150}
					    C 140 ${y + 60}, 140 ${y - 50}, 95 ${y - 95}
					    C 40 ${y - 60}, -60 ${y - 70}, -110 ${y - 85}
					    C -150 ${y - 40}, -140 ${y + 60}, -150 ${y + 150} Z`}
					fill={c}
					stroke={KONTUR}
					strokeWidth={K - 2}
					strokeLinejoin="round"
				/>
			);
		case 'bun':
			return (
				<>
					<circle cx={0} cy={y - 185} r={58} fill={c} stroke={KONTUR} strokeWidth={K - 2} />
					<path
						d={`M -158 ${y} C -160 ${y - 130}, -80 ${y - 170}, 0 ${y - 170} C 80 ${y - 170}, 160 ${y - 130}, 158 ${y}
						    C 120 ${y - 80}, 40 ${y - 105}, 0 ${y - 100} C -40 ${y - 105}, -120 ${y - 80}, -158 ${y} Z`}
						fill={c}
						stroke={KONTUR}
						strokeWidth={K - 2}
					/>
				</>
			);
		case 'cap':
			return (
				<>
					<path
						d={`M -150 ${y - 50} C -150 ${y - 175}, 150 ${y - 175}, 150 ${y - 50} Z`}
						fill={c}
						stroke={KONTUR}
						strokeWidth={K - 2}
					/>
					<path d={`M 60 ${y - 55} L 250 ${y - 40} L 250 ${y - 22} L 60 ${y - 30} Z`} fill={c} stroke={KONTUR} strokeWidth={K - 2} strokeLinejoin="round" />
				</>
			);
		case 'hat':
			// fotr sapka (dedektif / 1900'ler)
			return (
				<>
					<path d={`M -235 ${y - 95} C -120 ${y - 70}, 120 ${y - 70}, 235 ${y - 95} L 220 ${y - 70} C 100 ${y - 45}, -100 ${y - 45}, -220 ${y - 70} Z`} fill={c} stroke={KONTUR} strokeWidth={K - 2} strokeLinejoin="round" />
					<path d={`M -125 ${y - 85} C -130 ${y - 210}, -60 ${y - 245}, 0 ${y - 225} C 60 ${y - 245}, 130 ${y - 210}, 125 ${y - 85} Z`} fill={c} stroke={KONTUR} strokeWidth={K - 2} strokeLinejoin="round" />
					<path d={`M -122 ${y - 110} C -40 ${y - 98}, 40 ${y - 98}, 122 ${y - 110}`} stroke="#7a1f1f" strokeWidth={18} fill="none" />
				</>
			);
		case 'none':
		default:
			return null;
	}
};

const Yuz: React.FC<{g: Gorunum; ifade: Ifade; agiz: number; t: number; tohum: string; yon: 1 | -1}> = ({g, ifade, agiz, t, tohum, yon}) => {
	const y = KAFA_Y;
	const dx = yon * 14; // yuz hafifce bakis yonune kayar
	// Goz kirpma: her ~2.5-4 sn'de 0.12 sn
	const periyot = 2.6 + random(tohum) * 1.6;
	const kirp = (t + random(tohum + 'k') * 3) % periyot < 0.12;
	const iri = ifade === 'shocked' || ifade === 'scared';
	const gozY = y - 10;

	const goz = (x: number) =>
		kirp ? (
			<path d={`M ${x - 14} ${gozY} L ${x + 14} ${gozY}`} stroke={KONTUR} strokeWidth={7} strokeLinecap="round" />
		) : iri ? (
			<>
				<ellipse cx={x} cy={gozY} rx={24} ry={28} fill="#fff" stroke={KONTUR} strokeWidth={6} />
				<circle cx={x + yon * 4} cy={gozY + 3} r={9} fill={KONTUR} />
			</>
		) : (
			<ellipse cx={x} cy={gozY} rx={10} ry={15} fill={KONTUR} />
		);

	// Kaslar: ifadeye gore egim
	const kas = (x: number, sol: boolean) => {
		const ic = sol ? x + 20 : x - 20;
		const dis = sol ? x - 22 : x + 22;
		let icY = gozY - 48;
		let disY = gozY - 48;
		if (ifade === 'angry') icY += 16;
		if (ifade === 'sad' || ifade === 'scared') {
			icY -= 14;
			disY += 6;
		}
		if (ifade === 'shocked') {
			icY -= 22;
			disY -= 22;
		}
		if (ifade === 'thinking' && !sol) {
			icY -= 16;
			disY -= 16;
		}
		const ortaY = Math.min(icY, disY) - 8;
		return <path d={`M ${dis} ${disY} Q ${x} ${ortaY} ${ic} ${icY}`} stroke={KONTUR} strokeWidth={7} fill="none" strokeLinecap="round" />;
	};

	const agizY = y + 75;
	const ax = dx;
	let agizEl: React.ReactNode;
	if (agiz > 0.08) {
		// konusurken: koyu oval, acikliga gore yukseklik
		const h = 8 + agiz * 34;
		agizEl = (
			<ellipse cx={ax} cy={agizY} rx={22 + agiz * 6} ry={h / 2} fill="#3a1414" stroke={KONTUR} strokeWidth={6} />
		);
	} else if (ifade === 'shocked') {
		agizEl = <ellipse cx={ax} cy={agizY} rx={18} ry={24} fill="#3a1414" stroke={KONTUR} strokeWidth={6} />;
	} else if (ifade === 'happy') {
		agizEl = <path d={`M ${ax - 36} ${agizY - 8} Q ${ax} ${agizY + 30} ${ax + 36} ${agizY - 8}`} stroke={KONTUR} strokeWidth={7} fill="none" strokeLinecap="round" />;
	} else if (ifade === 'sad') {
		agizEl = <path d={`M ${ax - 32} ${agizY + 12} Q ${ax} ${agizY - 16} ${ax + 32} ${agizY + 12}`} stroke={KONTUR} strokeWidth={7} fill="none" strokeLinecap="round" />;
	} else if (ifade === 'scared') {
		agizEl = (
			<path
				d={`M ${ax - 34} ${agizY} q 8.5 -10 17 0 q 8.5 10 17 0 q 8.5 -10 17 0 q 8.5 10 17 0`}
				stroke={KONTUR}
				strokeWidth={6}
				fill="none"
				strokeLinecap="round"
			/>
		);
	} else if (ifade === 'thinking') {
		agizEl = <path d={`M ${ax - 26} ${agizY + 4} L ${ax + 22} ${agizY - 6}`} stroke={KONTUR} strokeWidth={7} strokeLinecap="round" />;
	} else {
		agizEl = <path d={`M ${ax - 30} ${agizY} L ${ax + 30} ${agizY}`} stroke={KONTUR} strokeWidth={7} strokeLinecap="round" />;
	}

	return (
		<>
			{kas(-52 + dx, true)}
			{kas(52 + dx, false)}
			{goz(-52 + dx)}
			{goz(52 + dx)}
			{g.glasses && (
				<>
					<rect x={-102 + dx} y={gozY - 34} width={88} height={64} rx={16} fill="rgba(255,255,255,0.12)" stroke="#6b4a2b" strokeWidth={8} />
					<rect x={14 + dx} y={gozY - 34} width={88} height={64} rx={16} fill="rgba(255,255,255,0.12)" stroke="#6b4a2b" strokeWidth={8} />
					<path d={`M ${-14 + dx} ${gozY - 6} L ${14 + dx} ${gozY - 6}`} stroke="#6b4a2b" strokeWidth={7} />
				</>
			)}
			{g.mustache ? (
				<>
					<path
						d={`M ${dx} ${agizY - 30} C ${dx - 30} ${agizY - 55}, ${dx - 95} ${agizY - 40}, ${dx - 120} ${agizY - 5}
						    C ${dx - 80} ${agizY - 18}, ${dx - 40} ${agizY - 12}, ${dx} ${agizY - 18}
						    C ${dx + 40} ${agizY - 12}, ${dx + 80} ${agizY - 18}, ${dx + 120} ${agizY - 5}
						    C ${dx + 95} ${agizY - 40}, ${dx + 30} ${agizY - 55}, ${dx} ${agizY - 30} Z`}
						fill={g.hairColor}
						stroke={KONTUR}
						strokeWidth={5}
						strokeLinejoin="round"
					/>
					{agizEl}
				</>
			) : (
				agizEl
			)}
		</>
	);
};

export const Karakter: React.FC<Props> = ({gorunum: g, ifade, poz, agiz, t, tohum, yon = 1}) => {
	const kafaId = `kafa-${tohum.replace(/[^a-z0-9]/gi, '')}`;
	return (
		<g>
			{bacaklar(poz, t)}
			{/* govde: altta genisleyen yuvarlak tisort */}
			<path
				d="M -118 -585 C -150 -585, -150 -560, -150 -520 L -168 -330 C -172 -290, -150 -275, -110 -275 L 110 -275 C 150 -275, 172 -290, 168 -330 L 150 -520 C 150 -560, 150 -585, 118 -585 Z"
				fill={g.shirt}
				stroke={KONTUR}
				strokeWidth={K}
				strokeLinejoin="round"
			/>
			{/* govdede hafif golge (referanstaki yumusak gradyan) */}
			<path d="M 60 -560 C 120 -540, 140 -420, 150 -300 L 110 -285 C 120 -400, 100 -500, 60 -560 Z" fill="rgba(0,0,0,0.08)" />
			{kollar(poz, t)}
			{/* boyun yok: kafa dogrudan govdenin ustunde, referanstaki gibi */}
			<defs>
				<radialGradient id={kafaId} cx="38%" cy="35%" r="70%">
					<stop offset="0%" stopColor={g.skin} />
					<stop offset="75%" stopColor={g.skin} />
					<stop offset="100%" stopColor="rgba(120,70,30,0.55)" />
				</radialGradient>
			</defs>
			{(g.hair === 'long') && <Sac g={g} />}
			<circle cx={0} cy={KAFA_Y} r={KAFA_R} fill={`url(#${kafaId})`} stroke={KONTUR} strokeWidth={K} />
			<circle cx={0} cy={KAFA_Y} r={KAFA_R - 4} fill={g.skin} opacity={0.55} />
			{g.hair !== 'long' && <Sac g={g} />}
			{g.beard && (
				<path
					d={`M -140 ${KAFA_Y + 40} C -120 ${KAFA_Y + 170}, 120 ${KAFA_Y + 170}, 140 ${KAFA_Y + 40} C 100 ${KAFA_Y + 110}, -100 ${KAFA_Y + 110}, -140 ${KAFA_Y + 40} Z`}
					fill={g.hairColor}
					stroke={KONTUR}
					strokeWidth={6}
				/>
			)}
			<Yuz g={g} ifade={ifade} agiz={agiz} t={t} tohum={tohum} yon={yon} />
		</g>
	);
};
