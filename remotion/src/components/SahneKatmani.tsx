import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import type {Kamera, Sahne} from '../types';

// Kamera hareketi: 0..1 ilerlemeye gore olcek / kaydirma / donme.
// Ilerleme yumusak (ease-in-out) -> "elle cekilmis" degil "animasyon kamerasi" hissi.
const kameraDurumu = (kamera: Kamera, p: number) => {
	switch (kamera) {
		case 'pushIn':
			return {s: interpolate(p, [0, 1], [1.06, 1.3]), x: 0, y: interpolate(p, [0, 1], [0, -1.5]), r: 0};
		case 'pullOut':
			return {s: interpolate(p, [0, 1], [1.32, 1.08]), x: 0, y: 0, r: 0};
		case 'panLeft':
			return {s: 1.24, x: interpolate(p, [0, 1], [5, -5]), y: 0, r: 0};
		case 'panRight':
			return {s: 1.24, x: interpolate(p, [0, 1], [-5, 5]), y: 0, r: 0};
		case 'tiltUp':
			return {s: 1.22, x: 0, y: interpolate(p, [0, 1], [5, -5]), r: 0};
		case 'tiltDown':
			return {s: 1.22, x: 0, y: interpolate(p, [0, 1], [-5, 5]), r: 0};
		case 'dutch':
		default:
			return {s: interpolate(p, [0, 1], [1.16, 1.28]), x: 0, y: 0, r: interpolate(p, [0, 1], [-2.2, 2.2])};
	}
};

const ProsedurelArkaPlan: React.FC<{tohum: number}> = ({tohum}) => {
	const frame = useCurrentFrame();
	const aci = (tohum * 47) % 360;
	return (
		<AbsoluteFill
			style={{
				background: `radial-gradient(circle at ${30 + (tohum % 4) * 12}% ${25 + Math.sin(frame / 40) * 4}%, rgba(120,170,200,0.45), transparent 38%),
					linear-gradient(${aci}deg, #05070c 0%, #0d1a26 55%, #1a120b 100%)`,
			}}
		/>
	);
};

export const SahneKatmani: React.FC<{sahne: Sahne; sureKare: number; sira: number; canli?: boolean}> = ({sahne, sureKare, sira, canli}) => {
	const frame = useCurrentFrame();
	const p = Easing.inOut(Easing.cubic)(Math.min(1, Math.max(0, frame / Math.max(1, sureKare))));
	const k = kameraDurumu(sahne.camera, p);

	// "Nefes alan" 2.5D derinlik: ayni gorselin bulanik arka kopyasi daha yavas,
	// net on kopyasi (kenarlari maskeli) biraz daha hizli hareket eder -> parallax hissi.
	const nefes = Math.sin(frame / 22 + sira) * 0.6;

	// Gecis 'zoom' ise ilk karelerde hizli iceri dalis + hareket bulaniklik
	const dalis = sahne.transition === 'zoom' && sira > 0;
	const ekOlcek = dalis ? interpolate(frame, [0, 9], [1.35, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.exp)}) : 1;
	const bulanik = dalis ? interpolate(frame, [0, 9], [14, 0], {extrapolateRight: 'clamp'}) : 0;

	// Kanca: ilk sahne "carpma" ile acilir
	const carpma = sira === 0 ? interpolate(frame, [0, 10], [1.25, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.back(2))}) : 1;

	const medya = (stil: React.CSSProperties) => {
		if (!sahne.src) return <ProsedurelArkaPlan tohum={sira} />;
		const ortak: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', ...stil};
		return sahne.kind === 'video' ? (
			<OffthreadVideo src={staticFile(sahne.src)} muted style={ortak} />
		) : (
			<Img src={staticFile(sahne.src)} style={ortak} />
		);
	};

	// Olcek asla 1.02'nin altina inmesin: aksi halde kenarlarda siyah cerceve gorunur
	// (kanca 'carpma'si geri sekerken ve video katmaninda olcek < 1 oluyordu).
	const donusum = (carpan: number, ek: number) =>
		`scale(${Math.max(1.02, (k.s + ek) * ekOlcek * carpma)}) translate(${k.x * carpan}%, ${(k.y + nefes) * carpan}%) rotate(${k.r}deg)`;

	if (sahne.kind === 'video') {
		// Gercek klip zaten hareketli: tek katman yeter (iki kez video cozmek render'i yavaslatir)
		return (
			<AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
				<AbsoluteFill style={{transform: donusum(0.5, 0), filter: `blur(${bulanik}px) contrast(1.1) saturate(0.8)`}}>
					{medya({})}
				</AbsoluteFill>
			</AbsoluteFill>
		);
	}

	return (
		<AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
			{/* Arka derinlik katmani: Python onceden bulaniklastirdi (canli CSS blur cok yavas) */}
			<AbsoluteFill style={{transform: donusum(0.6, 0.06)}}>
				{sahne.bg ? (
					<Img src={staticFile(sahne.bg)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				) : (
					<AbsoluteFill style={{filter: 'blur(10px) brightness(0.7)'}}>{medya({})}</AbsoluteFill>
				)}
			</AbsoluteFill>
			<AbsoluteFill
				style={{
					transform: donusum(1, 0),
					filter: (bulanik > 0.5 ? `blur(${bulanik}px) ` : '') + (canli ? 'contrast(1.03) saturate(1.06)' : 'contrast(1.12) saturate(0.82) brightness(0.92)'),
					WebkitMaskImage: 'radial-gradient(ellipse 78% 70% at 50% 46%, #000 62%, transparent 100%)',
					maskImage: 'radial-gradient(ellipse 78% 70% at 50% 46%, #000 62%, transparent 100%)',
				}}
			>
				{medya({})}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};
