import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {AltyaziGrubu} from '../types';

const temizle = (w: string) => w.toLowerCase().replace(/[^a-z0-9']/g, '');

// Kelime kelime "karaoke" altyazi: aktif kelime sari + buyur, anahtar kelimeler kirmizi kutuda.
export const Altyazi: React.FC<{gruplar: AltyaziGrubu[]; anahtarlar: string[]}> = ({gruplar, anahtarlar}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = frame / fps;
	const anahtar = new Set(anahtarlar.map(temizle));

	// Bir sonraki grup gelene kadar mevcut grup ekranda kalir (bos ekran = kaydirma)
	let aktif = -1;
	for (let i = 0; i < gruplar.length; i++) {
		if (gruplar[i].start <= t) aktif = i;
	}
	if (aktif < 0) return null;
	const g = gruplar[aktif];
	const sonraki = gruplar[aktif + 1];
	if (!sonraki && t > g.end + 0.8) return null;

	const girisKare = Math.round(g.start * fps);
	const giris = spring({frame: frame - girisKare, fps, config: {damping: 11, stiffness: 220, mass: 0.6}});
	const olcek = interpolate(giris, [0, 1], [0.55, 1]);
	const yukari = interpolate(giris, [0, 1], [40, 0]);

	return (
		<div
			style={{
				position: 'absolute',
				left: 60,
				right: 60,
				top: '60%',
				display: 'flex',
				flexWrap: 'wrap',
				justifyContent: 'center',
				gap: '6px 26px',
				transform: `translateY(${yukari}px) scale(${olcek})`,
				opacity: Math.min(1, giris * 1.6),
			}}
		>
			{g.words.map((w, i) => {
				const konusuluyor = t >= w.start - 0.03;
				const simdi = t >= w.start - 0.03 && t < w.end + 0.05;
				const ham = temizle(w.word);
				const vurgu = anahtar.has(ham) || /\d/.test(ham);
				const zipla = simdi
					? spring({frame: frame - Math.round(w.start * fps), fps, config: {damping: 9, stiffness: 300}})
					: 0;
				return (
					<span
						key={i}
						style={{
							fontFamily: 'Anton, Impact, sans-serif',
							fontSize: 118,
							lineHeight: 1.08,
							letterSpacing: 1,
							textTransform: 'uppercase',
							color: vurgu ? '#ffffff' : konusuluyor ? (simdi ? '#ffe14d' : '#ffffff') : 'rgba(255,255,255,0.55)',
							WebkitTextStroke: '10px #000',
							paintOrder: 'stroke fill',
							textShadow: '0 8px 24px rgba(0,0,0,0.85)',
							transform: `translateY(${-zipla * 10}px) rotate(${simdi ? -2 : 0}deg)`,
							transformOrigin: 'center bottom',
							display: 'inline-block',
							padding: vurgu ? '0 14px' : 0,
							background: vurgu && konusuluyor ? '#d10f0f' : 'transparent',
							borderRadius: 10,
							boxShadow: vurgu && konusuluyor ? '0 0 30px rgba(255,0,0,0.55)' : 'none',
						}}
					>
						{w.word.replace(/[",]/g, '')}
					</span>
				);
			})}
		</div>
	);
};
