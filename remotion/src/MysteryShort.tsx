import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {Altyazi} from './components/Altyazi';
import {Atmosfer, FilmKatmani, IlerlemeCubugu} from './components/Atmosfer';
import {DosyaKarti} from './components/DosyaKarti';
import {Gecis} from './components/Gecis';
import {Cta, Logo, Manset} from './components/Marka';
import {SahneKatmani} from './components/SahneKatmani';
import type {ShortProps} from './types';

loadFont({family: 'Anton', url: staticFile('Anton-Regular.ttf')});

const KART_SN = 3.6;
const CTA_SN = 2.4;
// Sahneler kesisir: bir sonraki sahnenin gecisi oynarken eskisi altta kalir -> siyah kare olmaz
const ORTUSME_KARE = 2;

export const MysteryShort: React.FC<ShortProps> = (p) => {
	const {fps, durationInFrames} = useVideoConfig();
	const kare = (sn: number) => Math.max(0, Math.round(sn * fps));

	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			{p.scenes.map((s, i) => {
				const bas = kare(s.start);
				const son = i === p.scenes.length - 1 ? durationInFrames : kare(s.end) + ORTUSME_KARE;
				const sure = Math.max(1, son - bas);
				return (
					<Sequence key={`s${i}`} from={bas} durationInFrames={sure} layout="none">
						<AbsoluteFill>
							<SahneKatmani sahne={s} sureKare={sure} sira={i} canli={!!p.cizgi} />
							{i > 0 && <Gecis tur={s.transition} tohum={i} />}
						</AbsoluteFill>
					</Sequence>
				);
			})}

			{!p.cizgi && <Atmosfer />}

			{/* Altyazi okunurlugu icin alt yarida yumusak karartma */}
			<AbsoluteFill style={{background: 'linear-gradient(180deg, transparent 45%, rgba(0,0,0,0.55) 75%, rgba(0,0,0,0.25) 100%)'}} />

			<Manset metin={p.headline} />

			{p.caseCard && (
				<Sequence from={kare(p.caseCard.start)} durationInFrames={kare(KART_SN)} layout="none">
					<DosyaKarti kart={p.caseCard} sureKare={kare(KART_SN)} />
				</Sequence>
			)}

			<Altyazi gruplar={p.captions} anahtarlar={p.keywords} />

			{p.subscribeAt > 0 && (
				<Sequence from={kare(p.subscribeAt)} durationInFrames={kare(CTA_SN)} layout="none">
					<Cta metin="SUBSCRIBE" sureKare={kare(CTA_SN)} />
				</Sequence>
			)}
			{p.watchNextAt > 0 && (
				<Sequence from={kare(p.watchNextAt)} layout="none">
					<Cta metin="WATCH NEXT" sureKare={durationInFrames - kare(p.watchNextAt) + 30} renk="#111" />
				</Sequence>
			)}

			<Logo src={p.logo} />
			{!p.cizgi && <FilmKatmani />}
			<IlerlemeCubugu />

			{/* --- SES --- */}
			{p.audio && <Audio src={staticFile(p.audio)} />}
			{p.ambient && <Audio src={staticFile(p.ambient)} volume={0.55} />}
			{p.sfx.boom && <Audio src={staticFile(p.sfx.boom)} volume={0.9} />}
			{p.sfx.whoosh &&
				p.scenes.slice(1).map((s, i) => (
					<Sequence key={`w${i}`} from={Math.max(0, kare(s.start) - 3)} durationInFrames={kare(1)} layout="none">
						<Audio src={staticFile(p.sfx.whoosh as string)} volume={0.32} />
					</Sequence>
				))}
			{p.sfx.hit && p.caseCard && (
				<Sequence from={kare(p.caseCard.start) + 34} durationInFrames={kare(1.2)} layout="none">
					<Audio src={staticFile(p.sfx.hit)} volume={0.7} />
				</Sequence>
			)}
		</AbsoluteFill>
	);
};
