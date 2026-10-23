import React from 'react';
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Ustte sabit, carpici baslik (thumbnail yazisi): ilk saniyede ekrana carpar.
export const Manset: React.FC<{metin: string}> = ({metin}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	if (!metin) return null;
	const s = spring({frame, fps, config: {damping: 10, stiffness: 200}});
	const sallanma = frame < 14 ? Math.sin(frame * 2.2) * (14 - frame) * 0.9 : 0;
	return (
		<div style={{position: 'absolute', top: 120, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
			<div
				style={{
					transform: `scale(${interpolate(s, [0, 1], [2.4, 1])}) rotate(${-2 + sallanma * 0.2}deg) translateX(${sallanma}px)`,
					opacity: Math.min(1, s * 2),
					background: '#d10f0f',
					color: '#fff',
					fontFamily: 'Anton, Impact, sans-serif',
					fontSize: 84,
					letterSpacing: 2,
					padding: '8px 34px',
					borderRadius: 12,
					boxShadow: '0 12px 40px rgba(0,0,0,0.7), 0 0 40px rgba(255,0,0,0.35)',
					maxWidth: 960,
					textAlign: 'center',
					lineHeight: 1.1,
				}}
			>
				{metin.toUpperCase()}
			</div>
		</div>
	);
};

export const Logo: React.FC<{src: string | null}> = ({src}) => {
	if (!src) return null;
	return (
		<Img
			src={staticFile(src)}
			style={{position: 'absolute', right: 40, bottom: 70, width: 120, height: 120, borderRadius: '50%', opacity: 0.85, boxShadow: '0 0 20px rgba(0,0,0,0.8)'}}
		/>
	);
};

// Hap seklinde CTA: zipla-gir, kisa sure kal, kaybol.
export const Cta: React.FC<{metin: string; sureKare: number; renk?: string}> = ({metin, sureKare, renk = '#d10f0f'}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const s = spring({frame, fps, config: {damping: 9, stiffness: 220}});
	const cik = interpolate(frame, [sureKare - 8, sureKare], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const nabiz = 1 + Math.sin(frame / 4) * 0.03;
	return (
		<div style={{position: 'absolute', top: '44%', left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: cik}}>
			<div
				style={{
					transform: `scale(${interpolate(s, [0, 1], [0.2, 1]) * nabiz})`,
					display: 'flex',
					alignItems: 'center',
					gap: 20,
					background: renk,
					color: '#fff',
					fontFamily: 'Anton, Impact, sans-serif',
					fontSize: 70,
					letterSpacing: 3,
					padding: '14px 44px 14px 26px',
					borderRadius: 999,
					boxShadow: '0 14px 50px rgba(0,0,0,0.75)',
				}}
			>
				<div style={{width: 0, height: 0, borderTop: '22px solid transparent', borderBottom: '22px solid transparent', borderLeft: '36px solid #fff', marginLeft: 14}} />
				{metin}
			</div>
		</div>
	);
};
