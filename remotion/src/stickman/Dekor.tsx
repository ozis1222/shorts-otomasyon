import React from 'react';
import {KONTUR} from './Karakter';
import type {Arkaplan as ArkaplanTuru, Obje} from './tipler';

export const ZEMIN_Y = 1560; // karakterlerin bastigi cizgi

const K = 8;
const cizgi = {stroke: KONTUR, strokeWidth: K, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const};

// Referanstaki gibi soluk, duz renkli zeminler. Gizem kanali oldugu icin hafif koyu tonlar.
const RENK: Record<ArkaplanTuru, {ust: string; alt: string}> = {
	plain: {ust: '#8fb4b9', alt: '#7fa3a8'},
	room: {ust: '#c9b79c', alt: '#8a6a4f'},
	night: {ust: '#2f4a66', alt: '#22364b'},
	forest: {ust: '#7f9e8b', alt: '#4f6b4f'},
	sea: {ust: '#9cc3cf', alt: '#3f7491'},
	sky: {ust: '#a9cfe0', alt: '#cfe6ef'},
	office: {ust: '#b9c3c7', alt: '#7d8a90'},
	lab: {ust: '#c8dcd8', alt: '#8fa9a5'},
	snow: {ust: '#c6d6e2', alt: '#f2f6f8'},
	desert: {ust: '#e8c99a', alt: '#d2a86b'},
	cave: {ust: '#4b4440', alt: '#2f2a27'},
	street: {ust: '#33465c', alt: '#3d3d42'},
};

export const Arkaplan: React.FC<{tur: ArkaplanTuru; t: number}> = ({tur, t}) => {
	const r = RENK[tur] ?? RENK.plain;
	const yer = ZEMIN_Y;
	return (
		<svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
			<rect width={1080} height={1920} fill={r.ust} />
			{tur === 'plain' && <rect y={yer} width={1080} height={1920 - yer} fill={r.alt} />}
			{tur === 'room' && (
				<>
					<rect y={yer - 40} width={1080} height={1920 - yer + 40} fill={r.alt} />
					<rect y={yer - 60} width={1080} height={26} fill="#6e5440" />
					<rect x={90} y={360} width={190} height={240} fill="#e8dcc6" {...cizgi} />
					<path d="M 140 520 L 185 450 L 215 490 L 240 465 L 240 560 L 140 560 Z" fill="#9fb8a0" stroke={KONTUR} strokeWidth={5} />
				</>
			)}
			{(tur === 'night' || tur === 'street') && (
				<>
					<circle cx={830} cy={330} r={95} fill="#f3ecc8" {...cizgi} />
					<circle cx={800} cy={310} r={18} fill="#e2d9ae" />
					<circle cx={860} cy={360} r={12} fill="#e2d9ae" />
					{[...Array(14)].map((_, i) => (
						<circle key={i} cx={(i * 173) % 1040 + 20} cy={120 + ((i * 97) % 420)} r={3 + (i % 3)} fill="#fff" opacity={0.5 + 0.5 * Math.sin(t * 2 + i)} />
					))}
					<rect y={yer} width={1080} height={1920 - yer} fill={r.alt} />
					{tur === 'street' && (
						<>
							<rect x={0} y={yer - 520} width={260} height={520} fill="#253446" {...cizgi} />
							<rect x={60} y={yer - 450} width={60} height={80} fill="#f2d27a" stroke={KONTUR} strokeWidth={5} />
							<rect x={150} y={yer - 330} width={60} height={80} fill="#1b2633" stroke={KONTUR} strokeWidth={5} />
							<path d={`M 930 ${yer} L 930 ${yer - 640}`} stroke={KONTUR} strokeWidth={14} />
							<path d={`M 930 ${yer - 640} Q 930 ${yer - 700} 870 ${yer - 700}`} stroke={KONTUR} strokeWidth={12} fill="none" />
							<path d={`M 830 ${yer - 700} L 910 ${yer - 700} L 890 ${yer - 660} L 850 ${yer - 660} Z`} fill="#f2d27a" {...cizgi} />
							<path d={`M 850 ${yer - 660} L 760 ${yer} L 980 ${yer} L 890 ${yer - 660} Z`} fill="rgba(242,210,122,0.18)" />
						</>
					)}
				</>
			)}
			{tur === 'forest' && (
				<>
					<rect y={yer} width={1080} height={1920 - yer} fill={r.alt} />
					{[60, 250, 860, 1010].map((x, i) => (
						<g key={i}>
							<rect x={x - 22} y={yer - 330} width={44} height={330} fill="#6b4a33" {...cizgi} />
							<path d={`M ${x} ${yer - 760} L ${x + 150} ${yer - 300} L ${x - 150} ${yer - 300} Z`} fill={i % 2 ? '#3f6148' : '#4a6e52'} {...cizgi} />
						</g>
					))}
				</>
			)}
			{tur === 'sea' && (
				<>
					<rect y={yer - 120} width={1080} height={1920 - yer + 120} fill={r.alt} />
					{[0, 1, 2].map((i) => (
						<path
							key={i}
							d={`M -40 ${yer - 100 + i * 120} ${[...Array(9)].map((_, j) => `q 70 ${(j % 2 ? 1 : -1) * 26} 140 0`).join(' ')}`}
							transform={`translate(${Math.sin(t * 1.5 + i) * 30} 0)`}
							stroke="#e8f3f6"
							strokeWidth={8}
							fill="none"
							strokeLinecap="round"
						/>
					))}
				</>
			)}
			{tur === 'sky' && (
				<>
					{[
						[160, 380, 1],
						[760, 260, 0.8],
						[520, 1250, 1.2],
					].map(([x, y, s], i) => (
						<g key={i} transform={`translate(${x + Math.sin(t / 2 + i) * 25} ${y}) scale(${s})`}>
							<path d="M -120 40 C -170 40 -170 -30 -110 -30 C -100 -90 -10 -100 10 -50 C 50 -90 130 -60 120 0 C 170 0 170 40 120 40 Z" fill="#fff" {...cizgi} />
						</g>
					))}
				</>
			)}
			{tur === 'office' && (
				<>
					<rect y={yer - 40} width={1080} height={1920 - yer + 40} fill={r.alt} />
					<rect x={720} y={300} width={260} height={360} fill="#dde6ea" {...cizgi} />
					<path d="M 850 300 L 850 660 M 720 480 L 980 480" stroke={KONTUR} strokeWidth={6} />
					<rect x={80} y={420} width={210} height={150} fill="#f4f1e8" {...cizgi} />
					<path d="M 110 520 L 160 470 L 200 500 L 260 440" stroke="#c0392b" strokeWidth={8} fill="none" />
				</>
			)}
			{tur === 'lab' && (
				<>
					<rect y={yer - 40} width={1080} height={1920 - yer + 40} fill={r.alt} />
					<rect x={60} y={yer - 300} width={300} height={24} fill="#e9e9e9" {...cizgi} />
					<path d="M 120 1260 L 120 1180 L 150 1180 L 150 1260 Z" fill="#7ed6c1" {...cizgi} />
					<path d="M 200 1260 L 220 1150 L 250 1150 L 270 1260 Z" fill="#f2b5d4" {...cizgi} />
					<circle cx={310} cy={1225} r={35} fill="#b9e0f5" {...cizgi} />
				</>
			)}
			{tur === 'snow' && (
				<>
					<path d={`M 0 ${yer} L 0 ${yer - 380} L 220 ${yer - 700} L 430 ${yer - 380} L 600 ${yer - 560} L 820 ${yer - 260} L 1080 ${yer - 480} L 1080 ${yer} Z`} fill="#dfe8ef" {...cizgi} />
					<rect y={yer} width={1080} height={1920 - yer} fill={r.alt} />
					{[...Array(26)].map((_, i) => {
						const y = ((i * 131 + t * 90 * (0.6 + (i % 3) * 0.2)) % 1700) + 40;
						return <circle key={i} cx={(i * 211) % 1080 + Math.sin(t + i) * 20} cy={y} r={6 + (i % 3) * 2} fill="#fff" />;
					})}
				</>
			)}
			{tur === 'desert' && (
				<>
					<circle cx={820} cy={360} r={120} fill="#f6e3a1" {...cizgi} />
					<path d={`M 0 ${yer - 120} Q 300 ${yer - 300} 600 ${yer - 140} T 1080 ${yer - 160} L 1080 1920 L 0 1920 Z`} fill={r.alt} {...cizgi} />
				</>
			)}
			{tur === 'cave' && (
				<>
					<path d="M 0 0 L 1080 0 L 1080 260 L 980 330 L 900 250 L 800 360 L 700 260 L 600 340 L 480 250 L 380 350 L 280 260 L 160 340 L 0 250 Z" fill="#2a2522" {...cizgi} />
					<rect y={yer} width={1080} height={1920 - yer} fill={r.alt} />
					<circle cx={540} cy={900} r={420} fill="rgba(255,200,120,0.08)" />
				</>
			)}
			{/* zemin cizgisi */}
			<path d={`M 0 ${yer} L 1080 ${yer}`} stroke={KONTUR} strokeWidth={6} opacity={tur === 'sky' ? 0 : 0.6} />
		</svg>
	);
};

// Objeler: (0,0) objenin taban ortasi; boyutlar karakterle orantili (karakter ~930 px).
export const ObjeCiz: React.FC<{tur: Obje; t: number}> = ({tur, t}) => {
	switch (tur) {
		case 'door':
			return (
				<g>
					<rect x={-150} y={-640} width={300} height={640} fill="#8a5a3c" {...cizgi} />
					<rect x={-110} y={-590} width={220} height={250} fill="#9c6a49" stroke={KONTUR} strokeWidth={5} />
					<rect x={-110} y={-300} width={220} height={250} fill="#9c6a49" stroke={KONTUR} strokeWidth={5} />
					<circle cx={100} cy={-320} r={16} fill="#e6c35c" stroke={KONTUR} strokeWidth={5} />
				</g>
			);
		case 'window':
			return (
				<g>
					<rect x={-170} y={-900} width={340} height={380} fill="#24364a" {...cizgi} />
					<path d="M 0 -900 L 0 -520 M -170 -710 L 170 -710" stroke={KONTUR} strokeWidth={8} />
					<circle cx={80} cy={-820} r={30} fill="#f3ecc8" />
				</g>
			);
		case 'chair':
			return (
				<g transform="translate(280 -112) rotate(-90)">{/* devrilmis sandalye: yere yatik */}
					<rect x={-110} y={-300} width={220} height={30} fill="#a0703f" {...cizgi} />
					<rect x={70} y={-560} width={30} height={260} fill="#a0703f" {...cizgi} />
					<path d="M -95 -270 L -95 0 M 85 -270 L 85 0" stroke={KONTUR} strokeWidth={14} strokeLinecap="round" />
				</g>
			);
		case 'table':
			return (
				<g>
					<rect x={-230} y={-340} width={460} height={34} fill="#a0703f" {...cizgi} />
					<path d="M -200 -306 L -200 0 M 200 -306 L 200 0" stroke={KONTUR} strokeWidth={16} strokeLinecap="round" />
					<rect x={-80} y={-410} width={70} height={70} fill="#f4f1e8" {...cizgi} />
					<path d="M -10 -390 q 25 0 25 20 q 0 20 -25 20" fill="none" stroke={KONTUR} strokeWidth={6} />
				</g>
			);
		case 'phone': {
			const titre = Math.sin(t * 40) * 4;
			return (
				<g transform={`translate(${titre} 0)`}>
					<rect x={-80} y={-560} width={160} height={290} rx={26} fill="#2c2c2c" {...cizgi} />
					<rect x={-62} y={-530} width={124} height={220} rx={8} fill="#8fd0ff" />
					<path d="M -130 -480 q -20 30 0 60 M 130 -480 q 20 30 0 60" stroke={KONTUR} strokeWidth={6} fill="none" opacity={0.7} />
				</g>
			);
		}
		case 'radio':
			return (
				<g>
					<rect x={-170} y={-420} width={340} height={230} rx={20} fill="#8b6b4a" {...cizgi} />
					<circle cx={-80} cy={-305} r={60} fill="#3b2f25" {...cizgi} />
					<rect x={10} y={-370} width={120} height={50} fill="#f2d27a" stroke={KONTUR} strokeWidth={5} />
					<path d="M 120 -420 L 200 -560" stroke={KONTUR} strokeWidth={8} />
					{[0, 1, 2].map((i) => (
						<path key={i} d={`M ${215 + i * 25} ${-600 + i * 5} q 20 30 0 60`} stroke={KONTUR} strokeWidth={5} fill="none" opacity={0.4 + 0.6 * Math.abs(Math.sin(t * 4 - i))} />
					))}
				</g>
			);
		case 'map':
			return (
				<g>
					<path d="M -220 -760 L -80 -720 L 80 -760 L 220 -720 L 220 -360 L 80 -400 L -80 -360 L -220 -400 Z" fill="#efe1b8" {...cizgi} />
					<path d="M -150 -620 Q -40 -700 40 -600 T 160 -560" stroke="#c0392b" strokeWidth={7} strokeDasharray="18 14" fill="none" />
					<path d="M 140 -590 l 30 30 m 0 -30 l -30 30" stroke="#c0392b" strokeWidth={9} />
				</g>
			);
		case 'letter':
			return (
				<g transform="rotate(-6)">
					<rect x={-150} y={-720} width={300} height={380} fill="#f6f0dc" {...cizgi} />
					{[0, 1, 2, 3, 4, 5].map((i) => (
						<path key={i} d={`M -110 ${-660 + i * 50} L ${i === 5 ? 20 : 110} ${-660 + i * 50}`} stroke="#555" strokeWidth={6} strokeLinecap="round" />
					))}
				</g>
			);
		case 'clock': {
			const a = t * 30;
			return (
				<g>
					<circle cx={0} cy={-700} r={150} fill="#f6f0dc" {...cizgi} />
					<path d={`M 0 -700 L ${Math.sin(a / 57) * 90} ${-700 - Math.cos(a / 57) * 90}`} stroke={KONTUR} strokeWidth={9} strokeLinecap="round" />
					<path d="M 0 -700 L 55 -700" stroke={KONTUR} strokeWidth={11} strokeLinecap="round" />
					<circle cx={0} cy={-700} r={10} fill={KONTUR} />
				</g>
			);
		}
		case 'car':
			return (
				<g>
					<path d="M -280 -90 L -280 -220 L -170 -230 L -100 -330 L 120 -330 L 200 -230 L 280 -210 L 280 -90 Z" fill="#c0392b" {...cizgi} />
					<path d="M -80 -310 L 100 -310 L 160 -235 L -150 -235 Z" fill="#bfe3f2" stroke={KONTUR} strokeWidth={6} />
					<circle cx={-160} cy={-80} r={58} fill="#333" {...cizgi} />
					<circle cx={160} cy={-80} r={58} fill="#333" {...cizgi} />
				</g>
			);
		case 'ship': {
			const s = Math.sin(t * 1.8) * 4;
			return (
				<g transform={`rotate(${s})`}>
					<path d="M -300 -200 L 300 -200 L 230 -60 L -230 -60 Z" fill="#5d4037" {...cizgi} />
					<path d="M 0 -200 L 0 -640" stroke={KONTUR} strokeWidth={12} />
					<path d="M 10 -620 L 230 -260 L 10 -260 Z" fill="#f6f0dc" {...cizgi} />
					<path d="M -10 -560 L -190 -260 L -10 -260 Z" fill="#efe6cf" {...cizgi} />
				</g>
			);
		}
		case 'plane': {
			const y = Math.sin(t * 2) * 14;
			return (
				<g transform={`translate(0 ${y - 520})`}>
					<path d="M -300 0 C -300 -50 250 -60 300 -10 C 320 10 300 30 260 30 L -280 30 Z" fill="#e9eef1" {...cizgi} />
					<path d="M -40 -10 L 60 -180 L 120 -180 L 70 -10 Z" fill="#c9d3d8" {...cizgi} />
					<path d="M -260 -10 L -300 -120 L -250 -120 L -200 -15 Z" fill="#c0392b" {...cizgi} />
					{[0, 1, 2, 3].map((i) => (
						<circle key={i} cx={130 - i * 70} cy={0} r={14} fill="#8fd0ff" stroke={KONTUR} strokeWidth={4} />
					))}
				</g>
			);
		}
		case 'lighthouse':
			return (
				<g>
					<path d="M -110 0 L -70 -760 L 70 -760 L 110 0 Z" fill="#f4f1e8" {...cizgi} />
					<path d="M -98 -230 L 98 -230 L 92 -330 L -92 -330 Z M -83 -480 L 83 -480 L 78 -570 L -78 -570 Z" fill="#c0392b" />
					<rect x={-90} y={-880} width={180} height={120} fill="#f2d27a" {...cizgi} />
					<path d="M -110 -880 L 0 -960 L 110 -880 Z" fill="#c0392b" {...cizgi} />
					<path d={`M 90 -830 L 600 ${-930 + Math.sin(t * 2) * 60} L 600 ${-730 + Math.sin(t * 2) * 60} Z`} fill="rgba(255,236,160,0.35)" />
				</g>
			);
		case 'house':
			return (
				<g>
					<rect x={-230} y={-420} width={460} height={420} fill="#d8c3a5" {...cizgi} />
					<path d="M -270 -410 L 0 -650 L 270 -410 Z" fill="#7b4a3a" {...cizgi} />
					<rect x={-50} y={-200} width={100} height={200} fill="#5d4037" {...cizgi} />
					<rect x={-180} y={-330} width={90} height={90} fill="#2c3e50" {...cizgi} />
					<rect x={90} y={-330} width={90} height={90} fill="#f2d27a" {...cizgi} />
				</g>
			);
		case 'tree':
			return (
				<g>
					<rect x={-40} y={-420} width={80} height={420} fill="#6b4a33" {...cizgi} />
					<circle cx={0} cy={-560} r={210} fill="#4f7a55" {...cizgi} />
				</g>
			);
		case 'grave':
			return (
				<g>
					<path d="M -140 0 L -140 -330 C -140 -470 140 -470 140 -330 L 140 0 Z" fill="#a7a9ac" {...cizgi} />
					<path d="M 0 -380 L 0 -220 M -55 -320 L 55 -320" stroke={KONTUR} strokeWidth={12} strokeLinecap="round" />
				</g>
			);
		case 'box':
			return (
				<g>
					<rect x={-170} y={-300} width={340} height={300} fill="#c49a6c" {...cizgi} />
					<path d="M -170 -300 L -120 -380 L 220 -380 L 170 -300 M 170 0 L 220 -80 L 220 -380" fill="#b08458" {...cizgi} />
					<text x={0} y={-130} textAnchor="middle" fontSize={130} fontFamily="Anton, Impact" fill={KONTUR}>?</text>
				</g>
			);
		case 'key':
			return (
				<g transform={`translate(0 -560) rotate(${Math.sin(t * 2) * 10})`}>
					<circle cx={-120} cy={0} r={70} fill="#e6c35c" {...cizgi} />
					<circle cx={-120} cy={0} r={25} fill="none" stroke={KONTUR} strokeWidth={6} />
					<path d="M -50 -18 L 180 -18 L 180 18 L 150 18 L 150 60 L 115 60 L 115 18 L -50 18 Z" fill="#e6c35c" {...cizgi} />
				</g>
			);
		case 'footprints':
			return (
				<g>
					{[0, 1, 2, 3, 4].map((i) => (
						<ellipse key={i} cx={-260 + i * 130} cy={-20 - (i % 2) * 40} rx={34} ry={18} fill="#3a3a3a" opacity={0.75 - i * 0.12} />
					))}
				</g>
			);
		case 'camera':
			return (
				<g>
					<rect x={-180} y={-640} width={300} height={170} rx={20} fill="#3a3a3a" {...cizgi} />
					<path d="M 120 -600 L 220 -650 L 220 -460 L 120 -510 Z" fill="#555" {...cizgi} />
					<circle cx={-120} cy={-605} r={14} fill={Math.sin(t * 6) > 0 ? '#ff3b30' : '#5a1a1a'} />
					<path d="M -30 -470 L -30 0" stroke={KONTUR} strokeWidth={14} />
				</g>
			);
		case 'skull':
			return (
				<g transform="translate(0 -320)">
					<path d="M -150 0 C -170 -230 170 -230 150 0 C 150 60 110 70 90 80 L 90 140 L -90 140 L -90 80 C -110 70 -150 60 -150 0 Z" fill="#f4f1e8" {...cizgi} />
					<circle cx={-60} cy={-10} r={42} fill={KONTUR} />
					<circle cx={60} cy={-10} r={42} fill={KONTUR} />
					<path d="M 0 40 L -20 80 L 20 80 Z" fill={KONTUR} />
				</g>
			);
		case 'question': {
			const z = Math.sin(t * 3) * 12;
			return (
				<g transform={`translate(0 ${-640 + z})`}>
					<text x={0} y={0} textAnchor="middle" fontSize={420} fontFamily="Anton, Impact" fill="#f2d27a" stroke={KONTUR} strokeWidth={10} paintOrder="stroke">?</text>
				</g>
			);
		}
		case 'none':
		default:
			return null;
	}
};
