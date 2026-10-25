import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import type {Kamera, Sahne} from '../types';

// Kamera hareketi: 0..1 ilerlemeye gore olcek / kaydirma / donme.
// Ilerleme yumusak (ease-in-out) -> "elle cekilmis" degil "animasyon kamerasi" hissi.
// Yonetmen plani modunda (canli) hareketler olculu: hikayeye hizmet eden yavas yaklasma/kayma,
// rastgele sarsinti yok. 'static' = vurgu karesi (yalnizca algilanmayacak kadar hafif nefes).
const planliKamera = (kamera: Kamera, p: number) => {
	switch (kamera) {
		case 'pushIn':
			return {s: interpolate(p, [0, 1], [1.04, 1.16]), x: 0, y: interpolate(p, [0, 1], [0, -1]), r: 0};
		case 'pullOut':
			return {s: interpolate(p, [0, 1], [1.17, 1.04]), x: 0, y: 0, r: 0};
		case 'panLeft':
			return {s: 1.12, x: interpolate(p, [0, 1], [3.2, -3.2]), y: 0, r: 0};
		case 'panRight':
			return {s: 1.12, x: interpolate(p, [0, 1], [-3.2, 3.2]), y: 0, r: 0};
		case 'tiltUp':
			return {s: 1.12, x: 0, y: interpolate(p, [0, 1], [3, -3]), r: 0};
		case 'tiltDown':
			return {s: 1.12, x: 0, y: interpolate(p, [0, 1], [-3, 3]), r: 0};
		case 'static':
		case 'dutch':
		default:
			return {s: interpolate(p, [0, 1], [1.05, 1.07]), x: 0, y: 0, r: 0};
	}
};

const kameraDurumu = (kamera: Kamera, p: number) => {
	switch (kamera) {
		case 'static':
			return {s: 1.06, x: 0, y: 0, r: 0};
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
	const k = canli ? planliKamera(sahne.camera, p) : kameraDurumu(sahne.camera, p);

	// "Nefes alan" 2.5D derinlik: ayni gorselin bulanik arka kopyasi daha yavas,
	// net on kopyasi (kenarlari maskeli) biraz daha hizli hareket eder -> parallax hissi.
	const nefes = canli ? 0 : Math.sin(frame / 22 + sira) * 0.6;

	// Gecis 'zoom' ise ilk karelerde hizli iceri dalis + hareket bulaniklik
	const dalis = sahne.transition === 'zoom' && sira > 0;
	const ekOlcek = dalis ? interpolate(frame, [0, 9], [1.35, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.exp)}) : 1;
	const bulanik = dalis ? interpolate(frame, [0, 9], [14, 0], {extrapolateRight: 'clamp'}) : 0;

	// Kanca: ilk sahne "carpma" ile acilir (planli modda yok: ilk kare temiz ve okunur olmali)
	const carpma = sira === 0 && !canli ? interpolate(frame, [0, 10], [1.25, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.back(2))}) : 1;

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
			{sahne.light && sahne.light !== 'steady' && <IsikKatmani tur={sahne.light} sureKare={sureKare} sira={sira} />}
		</AbsoluteFill>
	);
};

// Isik degisimi: titreyen lamba, yavas kararma, karanliktan aciga cikma, simsek.
const IsikKatmani: React.FC<{tur: string; sureKare: number; sira: number}> = ({tur, sureKare, sira}) => {
	const frame = useCurrentFrame();
	const p = Math.min(1, frame / Math.max(1, sureKare));
	let karanlik = 0;
	let beyaz = 0;
	if (tur === 'flicker') {
		// deterministik, duzensiz kisa sonmeler (lamba/ampul)
		const n = Math.sin(frame * 1.7 + sira) * Math.sin(frame * 0.53 + sira * 3);
		karanlik = n > 0.82 ? 0.45 : n > 0.6 ? 0.18 : 0;
	} else if (tur === 'dim_down') {
		karanlik = interpolate(p, [0, 1], [0, 0.42]);
	} else if (tur === 'reveal') {
		karanlik = interpolate(frame, [0, Math.min(36, sureKare)], [0.75, 0], {extrapolateRight: 'clamp'});
	} else if (tur === 'lightning') {
		const t = frame % 75;
		beyaz = t < 3 ? 0.55 : t < 6 ? 0.15 : t < 8 ? 0.4 : 0;
		karanlik = 0.18;
	}
	return (
		<>
			{karanlik > 0 && <AbsoluteFill style={{backgroundColor: '#02040a', opacity: karanlik}} />}
			{beyaz > 0 && <AbsoluteFill style={{backgroundColor: '#dfe8ff', opacity: beyaz, mixBlendMode: 'screen'}} />}
		</>
	);
};
