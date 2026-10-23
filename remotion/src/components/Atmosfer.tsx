import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Suzulen toz/kul parcaciklari: deterministik (random(seed)) -> her render ayni sonucu verir.
const Toz: React.FC = () => {
	const frame = useCurrentFrame();
	const {width, height} = useVideoConfig();
	const parcalar = useMemo(
		() =>
			Array.from({length: 46}, (_, i) => ({
				x: random(`x${i}`) * width,
				y: random(`y${i}`) * height,
				r: 1.5 + random(`r${i}`) * 4.5,
				hiz: 0.25 + random(`h${i}`) * 0.9,
				salinim: 10 + random(`s${i}`) * 40,
				faz: random(`f${i}`) * Math.PI * 2,
				opak: 0.18 + random(`o${i}`) * 0.5,
			})),
		[width, height],
	);
	return (
		<AbsoluteFill style={{mixBlendMode: 'screen'}}>
			{parcalar.map((t, i) => {
				const y = (((t.y - frame * t.hiz * 2) % height) + height) % height;
				const x = t.x + Math.sin(frame / 30 + t.faz) * t.salinim;
				const parilti = 0.6 + 0.4 * Math.sin(frame / 9 + t.faz);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: x,
							top: y,
							width: t.r * 2,
							height: t.r * 2,
							borderRadius: '50%',
							background: 'radial-gradient(circle, rgba(255,236,200,1) 0%, rgba(255,236,200,0.5) 45%, transparent 70%)',
							opacity: t.opak * parilti,
						}}
					/>
				);
			})}
		</AbsoluteFill>
	);
};

// Yavasca suruklenen iki sis katmani
const Sis: React.FC = () => {
	const frame = useCurrentFrame();
	const a = frame / 30;
	return (
		<AbsoluteFill style={{mixBlendMode: 'screen', opacity: 0.32}}>
			<AbsoluteFill
				style={{
					background: `radial-gradient(ellipse 60% 22% at ${30 + Math.sin(a / 3) * 25}% 78%, rgba(170,195,215,0.75), rgba(170,195,215,0.25) 45%, transparent 75%),
						radial-gradient(ellipse 55% 18% at ${70 + Math.cos(a / 4) * 22}% 64%, rgba(150,175,200,0.6), rgba(150,175,200,0.2) 45%, transparent 75%)`,
				}}
			/>
			<AbsoluteFill
				style={{
					background: `radial-gradient(ellipse 70% 25% at ${50 + Math.sin(a / 5) * 30}% 92%, rgba(200,210,225,0.7), rgba(200,210,225,0.25) 45%, transparent 75%)`,
				}}
			/>
		</AbsoluteFill>
	);
};

// Ust koseden suzulen isik huzmesi (fener / pencere isigi hissi)
const IsikHuzmesi: React.FC = () => {
	const frame = useCurrentFrame();
	const aci = 200 + Math.sin(frame / 60) * 8;
	return (
		<AbsoluteFill
			style={{
				mixBlendMode: 'soft-light',
				opacity: 0.55,
				background: `conic-gradient(from ${aci}deg at 85% -5%, transparent 0deg, rgba(255,220,160,0.25) 4deg, rgba(255,220,160,0.5) 9deg, rgba(255,220,160,0.25) 14deg, transparent 19deg, rgba(255,220,160,0.18) 24deg, rgba(255,220,160,0.32) 27deg, transparent 33deg)`,
			}}
		/>
	);
};

// Ampul titremesi: arada bir kisa kararma -> gerilim
const Titreme: React.FC = () => {
	const frame = useCurrentFrame();
	const n = random(`t${Math.floor(frame / 2)}`);
	const koyu = n > 0.965 ? 0.38 : n > 0.9 ? 0.12 : 0;
	return <AbsoluteFill style={{backgroundColor: '#000', opacity: koyu}} />;
};

export const Atmosfer: React.FC = () => (
	<>
		<IsikHuzmesi />
		<Sis />
		<Toz />
		<Titreme />
	</>
);

// En ustte: film grain + vinyet + hafif renk gradesi (soguk golgeler, sicak isiklar)
export const FilmKatmani: React.FC = () => {
	const frame = useCurrentFrame();
	const tohum = frame % 24;
	return (
		<>
			<AbsoluteFill
				style={{
					background: 'linear-gradient(180deg, rgba(20,40,60,0.28) 0%, rgba(0,0,0,0) 40%, rgba(60,30,10,0.18) 100%)',
					mixBlendMode: 'overlay',
				}}
			/>
			<AbsoluteFill
				style={{
					background: 'radial-gradient(ellipse 85% 75% at 50% 45%, transparent 55%, rgba(0,0,0,0.78) 100%)',
				}}
			/>
			<AbsoluteFill
				style={{
					opacity: 0.2,
					mixBlendMode: 'overlay',
					backgroundImage: `url(${staticFile('grain.png')})`,
					backgroundSize: '384px 384px',
					backgroundPosition: `${Math.floor(random(`gx${tohum}`) * 384)}px ${Math.floor(random(`gy${tohum}`) * 384)}px`,
				}}
			/>
		</>
	);
};

// Ilerleme cubugu (retention: izleyici ne kadar kaldigini gorur)
export const IlerlemeCubugu: React.FC = () => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const p = interpolate(frame, [0, durationInFrames - 1], [0, 100]);
	return (
		<div style={{position: 'absolute', left: 0, bottom: 0, height: 10, width: '100%', background: 'rgba(255,255,255,0.12)'}}>
			<div
				style={{
					height: '100%',
					width: `${p}%`,
					background: 'linear-gradient(90deg, #b30000, #ff2a2a)',
					boxShadow: '0 0 18px rgba(255,40,40,0.9)',
				}}
			/>
		</div>
	);
};
