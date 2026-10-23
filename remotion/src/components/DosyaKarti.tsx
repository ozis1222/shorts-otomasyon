import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {DosyaKarti as Kart} from '../types';

const daktilo = (metin: string, kare: number, hiz = 1.4) => metin.slice(0, Math.max(0, Math.floor(kare * hiz)));

// "Gizli dosya" karti: kagit dokulu panel kayarak gelir, satirlar daktiloyla yazilir,
// sonunda kirmizi CLASSIFIED muhru carpar. Hikayenin GERCEK oldugunu hissettirir.
export const DosyaKarti: React.FC<{kart: Kart; sureKare: number}> = ({kart, sureKare}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const giris = spring({frame, fps, config: {damping: 14, stiffness: 160}});
	const cikis = interpolate(frame, [sureKare - 10, sureKare], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
	const x = interpolate(giris, [0, 1], [-1100, 0]) + cikis * 1100;
	const muhurKare = 34;
	const muhur = spring({frame: frame - muhurKare, fps, config: {damping: 8, stiffness: 260}});

	const satirlar: [string, string][] = [
		['SUBJECT', kart.name],
		['DATE', kart.year],
		['LOCATION', kart.place],
	].filter(([, v]) => !!v) as [string, string][];

	return (
		<div
			style={{
				position: 'absolute',
				left: 80,
				right: 80,
				top: 300,
				transform: `translateX(${x}px) rotate(-2.5deg)`,
				background: 'linear-gradient(160deg, #efe4c8 0%, #d9c9a3 100%)',
				borderRadius: 6,
				padding: '34px 40px 120px',
				boxShadow: '0 30px 80px rgba(0,0,0,0.75), inset 0 0 80px rgba(120,90,40,0.35)',
				fontFamily: '"Courier New", Courier, monospace',
				color: '#1d1a14',
			}}
		>
			<div style={{display: 'flex', justifyContent: 'space-between', borderBottom: '3px solid #1d1a14', paddingBottom: 12, marginBottom: 18}}>
				<span style={{fontSize: 40, fontWeight: 700, letterSpacing: 6}}>CASE FILE</span>
				<span style={{fontSize: 30, letterSpacing: 2, opacity: 0.7}}>No. {kart.year || '----'}</span>
			</div>
			{satirlar.map(([etiket, deger], i) => (
				<div key={etiket} style={{fontSize: 36, lineHeight: 1.4, fontWeight: 700}}>
					<span style={{opacity: 0.55}}>{etiket}: </span>
					{daktilo(deger.toUpperCase(), frame - 6 - i * 9)}
				</div>
			))}
			<div
				style={{
					position: 'absolute',
					right: 36,
					bottom: 14,
					transform: `rotate(-9deg) scale(${interpolate(muhur, [0, 1], [2.6, 1])})`,
					opacity: frame >= muhurKare ? Math.min(1, muhur * 1.5) : 0,
					border: '7px solid #c4121a',
					color: '#c4121a',
					padding: '6px 22px',
					fontFamily: 'Anton, Impact, sans-serif',
					fontSize: 54,
					letterSpacing: 6,
					background: 'rgba(239,228,200,0.3)',
				}}
			>
				CLASSIFIED
			</div>
		</div>
	);
};
