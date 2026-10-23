import React from 'react';
import {Composition} from 'remotion';
import {MysteryShort} from './MysteryShort';
import {ornekProps} from './ornek';
import type {ShortProps} from './types';
import {StickmanShort} from './stickman/StickmanShort';
import {ornekStickman} from './stickman/ornek';
import type {StickmanProps} from './stickman/tipler';

export const FPS = 30;
// Anlatim bittikten sonra son CTA'nin okunabilmesi icin kisa kuyruk
const KUYRUK_SN = 0.8;

export const RemotionRoot: React.FC = () => {
	return (
		<>
		{/* Varsayilan stil: referanstaki gibi kalin konturlu, konusan cop adam animasyonu */}
		<Composition
			id="StickmanShort"
			component={StickmanShort}
			width={1080}
			height={1920}
			fps={FPS}
			durationInFrames={Math.ceil((ornekStickman.duration + KUYRUK_SN) * FPS)}
			defaultProps={ornekStickman}
			calculateMetadata={({props}: {props: StickmanProps}) => ({
				durationInFrames: Math.ceil((props.duration + KUYRUK_SN) * FPS),
			})}
		/>
		<Composition
			id="MysteryShort"
			component={MysteryShort}
			width={1080}
			height={1920}
			fps={FPS}
			durationInFrames={Math.ceil((ornekProps.duration + KUYRUK_SN) * FPS)}
			defaultProps={ornekProps}
			calculateMetadata={({props}: {props: ShortProps}) => ({
				durationInFrames: Math.ceil((props.duration + KUYRUK_SN) * FPS),
			})}
		/>
		</>
	);
};
