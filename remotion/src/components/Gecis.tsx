import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';
import type {Gecis as GecisTuru} from '../types';

export const GECIS_KARE = 9;

// Sahne baslangicinda oynayan kisa gecis efekti (zoom gecisi SahneKatmani icinde).
export const Gecis: React.FC<{tur: GecisTuru; tohum: number}> = ({tur, tohum}) => {
	const frame = useCurrentFrame();
	const p = interpolate(frame, [0, GECIS_KARE], [1, 0], {extrapolateRight: 'clamp'});
	if (p <= 0) return null;

	if (tur === 'flash') {
		return <AbsoluteFill style={{backgroundColor: '#fff', opacity: p * 0.85, mixBlendMode: 'screen'}} />;
	}
	if (tur === 'iris') {
		const r = interpolate(frame, [0, GECIS_KARE], [0, 120], {extrapolateRight: 'clamp'});
		return <AbsoluteFill style={{background: `radial-gradient(circle at 50% 45%, transparent ${r}%, #000 ${r + 6}%)`}} />;
	}
	if (tur === 'glitch') {
		return (
			<AbsoluteFill>
				{Array.from({length: 7}, (_, i) => {
					const y = random(`gy${tohum}-${i}-${frame}`) * 100;
					const h = 2 + random(`gh${tohum}-${i}-${frame}`) * 9;
					const kay = (random(`gx${tohum}-${i}-${frame}`) - 0.5) * 140 * p;
					return (
						<div
							key={i}
							style={{
								position: 'absolute',
								left: 0,
								right: 0,
								top: `${y}%`,
								height: `${h}%`,
								transform: `translateX(${kay}px)`,
								background: i % 2 ? 'rgba(0,255,240,0.28)' : 'rgba(255,0,60,0.3)',
								mixBlendMode: 'screen',
							}}
						/>
					);
				})}
				<AbsoluteFill style={{backgroundColor: '#fff', opacity: p * 0.25}} />
			</AbsoluteFill>
		);
	}
	return null;
};
