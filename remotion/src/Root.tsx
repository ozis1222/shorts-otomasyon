import React from 'react';
import {Composition} from 'remotion';
import {MysteryShort} from './MysteryShort';
import {ornekProps} from './ornek';
import type {ShortProps} from './types';

export const FPS = 30;
// Anlatim bittikten sonra son CTA'nin okunabilmesi icin kisa kuyruk
const KUYRUK_SN = 0.8;

export const RemotionRoot: React.FC = () => {
	return (
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
	);
};
