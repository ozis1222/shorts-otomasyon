import React from 'react';
import {AbsoluteFill, Audio, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {Altyazi} from '../components/Altyazi';
import {IlerlemeCubugu} from '../components/Atmosfer';
import {DosyaKarti} from '../components/DosyaKarti';
import {Cta, Logo, Manset} from '../components/Marka';
import {Arkaplan, ObjeCiz, ZEMIN_Y} from './Dekor';
import {Karakter, KONTUR} from './Karakter';
import type {Gorunum, StickmanProps, StickSahne} from './tipler';

loadFont({family: 'Anton', url: staticFile('Anton-Regular.ttf')});

const KART_SN = 3.6;
const CTA_SN = 2.4;

const VARSAYILAN: Gorunum = {skin: '#e8b07a', shirt: '#f4f4f4', hair: 'none', hairColor: '#2b2b2b', glasses: false, mustache: false, beard: false};

// Anlatici o an bir kelime soyluyorsa agiz acilip kapanir (hece ritmi ~ 9 Hz).
const agizAcikligi = (words: StickmanProps['words'], t: number) => {
	for (const w of words) {
		if (t >= w.start && t <= w.end) {
			const ilerleme = (t - w.start) / Math.max(0.05, w.end - w.start);
			return 0.35 + 0.65 * Math.abs(Math.sin(ilerleme * Math.PI * Math.max(1, Math.round((w.end - w.start) * 6))));
		}
		if (w.start > t) break;
	}
	return 0;
};

type Yer = {x: number; s: number};
const yerlesim = (n: number, obje: boolean): {kar: Yer[]; obje: Yer | null} => {
	// Shorts'ta karakterler buyuk olmali: tek karakter ekrani doldurur
	if (n <= 1) return obje ? {kar: [{x: 320, s: 1.02}], obje: {x: 800, s: 0.85}} : {kar: [{x: 540, s: 1.14}], obje: null};
	return obje
		? {kar: [{x: 230, s: 0.8}, {x: 850, s: 0.8}], obje: {x: 540, s: 0.62}}
		: {kar: [{x: 290, s: 0.94}, {x: 800, s: 0.94}], obje: null};
};

const Sahne: React.FC<{sahne: StickSahne; p: StickmanProps; sira: number; sureKare: number}> = ({sahne, p, sira, sureKare}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const yerelT = frame / fps;
	const globalT = sahne.start + yerelT;
	const karakterler = sahne.characters.slice(0, 2);
	const objeVar = !!sahne.propSvg || (sahne.prop && sahne.prop !== 'none');
	const yer = yerlesim(karakterler.length, !!objeVar);
	const agiz = agizAcikligi(p.words, globalT);
	// Tabela; dosya karti veya SUBSCRIBE / WATCH NEXT ekrandayken gizlenir (ust uste binmesin)
	const ustBos =
		!(p.caseCard && globalT >= p.caseCard.start && globalT <= p.caseCard.start + KART_SN) &&
		!(p.subscribeAt > 0 && globalT >= p.subscribeAt - 0.1 && globalT <= p.subscribeAt + CTA_SN) &&
		!(p.watchNextAt > 0 && globalT >= p.watchNextAt - 0.1);

	// Kamera: sahne boyunca yavas yaklasma; tek/cift sahnelerde yon degisir
	const zoom = interpolate(frame, [0, sureKare], [1, 1.07]);
	const kayma = (sira % 2 ? -1 : 1) * interpolate(frame, [0, sureKare], [0, 18]);
	// Giris: hafif "pop" (yeni sahne ekrana oturur)
	const giris = spring({frame, fps, config: {damping: 13, stiffness: 180}});

	return (
		<AbsoluteFill style={{transform: `scale(${zoom * interpolate(giris, [0, 1], [1.06, 1])}) translateX(${kayma}px)`, transformOrigin: '50% 75%'}}>
			{sahne.bgSvg ? (
				// Hikayeye ozel cizilmis sahne (Gemini SVG): hafif parallax icin karakterlerden yavas kayar
				<AbsoluteFill style={{transform: `translateX(${-kayma * 0.5}px)`}}>
					<Img src={staticFile(sahne.bgSvg)} style={{width: 1080, height: 1920}} />
				</AbsoluteFill>
			) : (
				<Arkaplan tur={sahne.background} t={yerelT} />
			)}
			<svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
				{objeVar && yer.obje && (
					<g transform={`translate(${yer.obje.x} ${ZEMIN_Y}) scale(${yer.obje.s * interpolate(giris, [0, 1], [0.6, 1])})`}>
						{sahne.propSvg ? (
							// anahtar obje: hafif suzulme + sallanma, tabani zemine oturur
							<g transform={`translate(0 ${Math.sin(yerelT * 2) * 8}) rotate(${Math.sin(yerelT * 1.3) * 2})`}>
								<image href={staticFile(sahne.propSvg)} x={-300} y={-620} width={600} height={600} />
							</g>
						) : (
							<ObjeCiz tur={sahne.prop} t={yerelT} />
						)}
					</g>
				)}
				{karakterler.map((k, i) => {
					const y = yer.kar[i] ?? yer.kar[0];
					const g = p.cast[k.role] ?? p.cast.narrator ?? VARSAYILAN;
					const gecikme = i * 4;
					const kg = spring({frame: frame - gecikme, fps, config: {damping: 11, stiffness: 170}});
					let dy = interpolate(kg, [0, 1], [260, 0]);
					let dx = 0;
					if (k.expression === 'shocked') {
						// sok: girisin hemen ardindan bir zipla + kisa titreme
						const z = Math.max(0, frame - gecikme - 8);
						dy -= Math.max(0, Math.sin(Math.min(z, 12) / 12 * Math.PI)) * 70;
						if (z < 18) dx = Math.sin(z * 2.8) * (18 - z) * 0.8;
					}
					if (k.expression === 'scared') dx = Math.sin(frame * 1.7 + i) * 3.5;
					// nefes: hafif dikey olcek
					const nefes = 1 + Math.sin(yerelT * 2.4 + i) * 0.008;
					const konusan = i === 0;
					const yon: 1 | -1 = karakterler.length > 1 ? (i === 0 ? 1 : -1) : objeVar ? 1 : 1;
					return (
						<g key={i} transform={`translate(${y.x + dx} ${ZEMIN_Y + dy}) scale(${y.s} ${y.s * nefes})`}>
							<ellipse cx={0} cy={6} rx={150} ry={20} fill="rgba(0,0,0,0.16)" />
							<Karakter
								gorunum={g}
								ifade={k.expression}
								poz={k.pose}
								agiz={konusan ? agiz : 0}
								t={yerelT + i * 0.7}
								tohum={`${k.role}-${sira}-${i}`}
								yon={yon}
							/>
						</g>
					);
				})}
			</svg>
			{sahne.label && ustBos ? (
				<div style={{position: 'absolute', top: 470, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
					<div
						style={{
							transform: `rotate(-3deg) scale(${interpolate(giris, [0, 1], [0.3, 1])})`,
							background: '#fffdf4',
							border: `7px solid ${KONTUR}`,
							borderRadius: 18,
							padding: '6px 34px',
							fontFamily: 'Anton, Impact, sans-serif',
							fontSize: sahne.label.length > 12 ? 64 : 86,
							color: KONTUR,
							boxShadow: '8px 8px 0 rgba(0,0,0,0.25)',
						}}
					>
						{sahne.label.toUpperCase()}
					</div>
				</div>
			) : null}
			{/* sahne gecisi: 4 karelik beyaz flas */}
			{sira > 0 && <AbsoluteFill style={{background: '#fff', opacity: interpolate(frame, [0, 4], [0.7, 0], {extrapolateRight: 'clamp'})}} />}
		</AbsoluteFill>
	);
};

// Kagit dokusu: referanstaki hafif grenli duz arka plan hissi
const KagitDokusu: React.FC = () => (
	<AbsoluteFill
		style={{
			opacity: 0.1,
			mixBlendMode: 'multiply',
			backgroundImage: `url(${staticFile('grain.png')})`,
			backgroundSize: '384px 384px',
		}}
	/>
);

export const StickmanShort: React.FC<StickmanProps> = (p) => {
	const {fps, durationInFrames} = useVideoConfig();
	const kare = (sn: number) => Math.max(0, Math.round(sn * fps));

	return (
		<AbsoluteFill style={{backgroundColor: '#8fb4b9'}}>
			{p.scenes.map((s, i) => {
				const bas = kare(s.start);
				const son = i === p.scenes.length - 1 ? durationInFrames : kare(s.end);
				const sure = Math.max(1, son - bas);
				return (
					<Sequence key={`s${i}`} from={bas} durationInFrames={sure} layout="none">
						<Sahne sahne={s} p={p} sira={i} sureKare={sure} />
					</Sequence>
				);
			})}
			<KagitDokusu />

			{!p.temiz && (
				<>
					<Manset metin={p.headline} />
					{p.caseCard && (
						<Sequence from={kare(p.caseCard.start)} durationInFrames={kare(KART_SN)} layout="none">
							<DosyaKarti kart={p.caseCard} sureKare={kare(KART_SN)} />
						</Sequence>
					)}
					<Altyazi gruplar={p.captions} anahtarlar={p.keywords} ust="79%" />
					{p.subscribeAt > 0 && (
						<Sequence from={kare(p.subscribeAt)} durationInFrames={kare(CTA_SN)} layout="none">
							<Cta metin="SUBSCRIBE" sureKare={kare(CTA_SN)} ust="19%" />
						</Sequence>
					)}
					{p.watchNextAt > 0 && (
						<Sequence from={kare(p.watchNextAt)} layout="none">
							<Cta metin="WATCH NEXT" sureKare={durationInFrames - kare(p.watchNextAt) + 30} renk="#111" ust="19%" />
						</Sequence>
					)}
					<Logo src={p.logo} />
					<IlerlemeCubugu />
				</>
			)}

			{/* --- SES --- */}
			{p.audio && <Audio src={staticFile(p.audio)} />}
			{p.sfx.boom && <Audio src={staticFile(p.sfx.boom)} volume={0.6} />}
			{p.scenes.slice(1).map((s, i) => (
				<React.Fragment key={`sfx${i}`}>
					{p.sfx.whoosh && (
						<Sequence from={Math.max(0, kare(s.start) - 3)} durationInFrames={kare(1)} layout="none">
							<Audio src={staticFile(p.sfx.whoosh)} volume={0.22} />
						</Sequence>
					)}
					{p.sfx.pop && (
						<Sequence from={kare(s.start) + 2} durationInFrames={kare(0.5)} layout="none">
							<Audio src={staticFile(p.sfx.pop)} volume={0.35} />
						</Sequence>
					)}
				</React.Fragment>
			))}
			{p.sfx.hit && p.caseCard && (
				<Sequence from={kare(p.caseCard.start) + 34} durationInFrames={kare(1.2)} layout="none">
					<Audio src={staticFile(p.sfx.hit)} volume={0.6} />
				</Sequence>
			)}
		</AbsoluteFill>
	);
};
