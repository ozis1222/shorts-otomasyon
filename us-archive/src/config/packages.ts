/**
 * Config-driven package tiers. Sections included in the final magazine and the
 * social-asset counts are all derived from here — nothing is hard-coded in the
 * renderer, so new tiers can be added by editing this file alone.
 */

export type SectionId =
  | 'cover'
  | 'our_numbers'
  | 'where_it_started'
  | 'message_timeline'
  | 'communication'
  | 'relationship_dna'
  | 'person_a'
  | 'person_b'
  | 'who_does_what'
  | 'emoji_language'
  | 'dictionary'
  | 'inside_jokes'
  | 'awards'
  | 'late_night'
  | 'most_active'
  | 'eras'
  | 'memorable'
  | 'fun_stats'
  | 'timeline'
  | 'fingerprint'
  | 'year_by_year'
  | 'if_we_were'
  | 'future_letter'
  | 'closing';

export interface PackageTier {
  id: string;
  name: string;
  tagline: string;
  /** Ordered sections rendered into the PDF magazine. */
  sections: SectionId[];
  assets: {
    storyCards: number; // 1080x1920
    instagramCards: number; // 1080x1350
    phoneWallpapers: number;
    desktopWallpapers: number;
    fingerprintPoster: boolean;
  };
}

const FULL_SECTIONS: SectionId[] = [
  'cover',
  'our_numbers',
  'where_it_started',
  'message_timeline',
  'communication',
  'relationship_dna',
  'person_a',
  'person_b',
  'who_does_what',
  'emoji_language',
  'dictionary',
  'inside_jokes',
  'awards',
  'late_night',
  'most_active',
  'eras',
  'memorable',
  'fun_stats',
  'timeline',
  'fingerprint',
  'year_by_year',
  'if_we_were',
  'future_letter',
  'closing',
];

export const PACKAGES: Record<string, PackageTier> = {
  mini: {
    id: 'mini',
    name: 'Mini',
    tagline: 'The highlights, beautifully told.',
    sections: [
      'cover',
      'our_numbers',
      'communication',
      'relationship_dna',
      'who_does_what',
      'emoji_language',
      'awards',
      'fingerprint',
      'closing',
    ],
    assets: {
      storyCards: 3,
      instagramCards: 2,
      phoneWallpapers: 1,
      desktopWallpapers: 0,
      fingerprintPoster: true,
    },
  },
  full: {
    id: 'full',
    name: 'Full Archive',
    tagline: 'Your whole story, from the first message on.',
    sections: FULL_SECTIONS,
    assets: {
      storyCards: 10,
      instagramCards: 5,
      phoneWallpapers: 3,
      desktopWallpapers: 1,
      fingerprintPoster: true,
    },
  },
  vault: {
    id: 'vault',
    name: 'The Vault',
    tagline: 'Everything, plus posters worth framing.',
    sections: FULL_SECTIONS,
    assets: {
      storyCards: 14,
      instagramCards: 8,
      phoneWallpapers: 4,
      desktopWallpapers: 2,
      fingerprintPoster: true,
    },
  },
};

export function getPackage(id: string): PackageTier {
  const pkg = PACKAGES[id];
  if (!pkg) throw new Error(`Unknown package tier: ${id}`);
  return pkg;
}
