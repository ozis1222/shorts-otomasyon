import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';

// Prosedurel ortam efektleri (harici dosya yok, deterministik): sahneye "yasam" katar.
// toz: isikta suzulen zerreler | yagmur: egik cizgiler | kar: yavas dusen taneler
// sis: yavas kayan katmanlar | kabarcik: yukselen hava kabarciklari | kivilcim: yukselen kor parcalari
export const Ortam: React.FC<{tur: string; sira: number}> = ({tur, sira}) => {
	const frame = useCurrentFrame();
	const {width, height, fps} = useVideoConfig();
	const t = frame / fps;
	const r = (k: string) => random(`${tur}-${sira}-${k}`);

	if (tur === 'sis') {
		return (
			<AbsoluteFill style={{pointerEvents: 'none'}}>
				{[0, 1, 2].map((i) => {
					const x = ((r(`x${i}`) * 100 + t * (6 + i * 3)) % 160) - 30;
					return (
						<div
							key={i}
							style={{
								position: 'absolute',
								left: `${x}%`,
								top: `${30 + i * 22 + r(`y${i}`) * 10}%`,
								width: '90%',
								height: '28%',
								transform: 'translateX(-50%)',
								background: 'radial-gradient(ellipse at center, rgba(170,185,210,0.20), transparent 70%)',
								filter: 'blur(18px)',
							}}
						/>
					);
				})}
			</AbsoluteFill>
		);
	}

	const ayar: Record<string, {n: number; hiz: number; boy: [number, number]; renk: string; yon: 1 | -1}> = {
		toz: {n: 34, hiz: 18, boy: [2, 5], renk: 'rgba(255,226,170,0.55)', yon: -1},
		kar: {n: 70, hiz: 120, boy: [4, 9], renk: 'rgba(240,245,255,0.85)', yon: 1},
		kabarcik: {n: 26, hiz: 160, boy: [6, 18], renk: 'rgba(200,230,255,0.5)', yon: -1},
		kivilcim: {n: 22, hiz: 140, boy: [3, 6], renk: 'rgba(255,170,60,0.9)', yon: -1},
		yagmur: {n: 90, hiz: 2200, boy: [2, 3], renk: 'rgba(190,210,235,0.45)', yon: 1},
	};
	const a = ayar[tur];
	if (!a) return null;

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			{Array.from({length: a.n}, (_, i) => {
				const bas = r(`b${i}`);
				const boy = a.boy[0] + r(`s${i}`) * (a.boy[1] - a.boy[0]);
				const hiz = a.hiz * (0.6 + r(`v${i}`) * 0.8);
				const yol = (bas * height + t * hiz) % (height + 60);
				const y = a.yon === 1 ? yol - 30 : height + 30 - yol;
				const salinim = tur === 'yagmur' ? 0 : Math.sin(t * (0.6 + r(`f${i}`)) + i) * (tur === 'toz' ? 24 : 14);
				const x = r(`x${i}`) * width + salinim + (tur === 'yagmur' ? (yol * 0.18) % width : 0);
				const parlak = tur === 'toz' || tur === 'kivilcim' ? 0.4 + 0.6 * Math.abs(Math.sin(t * 1.3 + i)) : 1;
				if (tur === 'yagmur') {
					return (
						<div
							key={i}
							style={{position: 'absolute', left: x % width, top: y, width: 2, height: 46 + boy * 10, background: a.renk, transform: 'rotate(12deg)'}}
						/>
					);
				}
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: x,
							top: y,
							width: boy,
							height: boy,
							borderRadius: '50%',
							background: tur === 'kabarcik' ? 'transparent' : a.renk,
							border: tur === 'kabarcik' ? `2px solid ${a.renk}` : 'none',
							boxShadow: tur === 'kivilcim' ? '0 0 10px rgba(255,140,40,0.9)' : tur === 'toz' ? '0 0 6px rgba(255,220,160,0.6)' : 'none',
							opacity: parlak,
						}}
					/>
				);
			})}
		</AbsoluteFill>
	);
};
