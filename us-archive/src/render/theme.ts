/**
 * The Us Archive design system. Editorial, premium, whitespace-forward — closer
 * to a coffee-table magazine than a template. Two themes ship (light + dark);
 * the token shape lets more be added without touching the renderer.
 */
export interface Theme {
  id: 'light' | 'dark';
  bg: string;
  surface: string;
  ink: string;
  inkSoft: string;
  hair: string;
  accent: string;
  accent2: string;
  accents: string[];
  serif: string;
  sans: string;
}

export const THEMES: Record<'light' | 'dark', Theme> = {
  light: {
    id: 'light',
    bg: '#F7F4EF',
    surface: '#FFFFFF',
    ink: '#1A1A1A',
    inkSoft: '#6B6660',
    hair: '#E4DED4',
    accent: '#E4572E',
    accent2: '#2E86AB',
    accents: ['#E4572E', '#F3A712', '#2E86AB', '#8A4FFF', '#3BB273'],
    serif: "'Fraunces', Georgia, 'Times New Roman', serif",
    sans: "'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif",
  },
  dark: {
    id: 'dark',
    bg: '#0E0E12',
    surface: '#16161C',
    ink: '#F5F5F0',
    inkSoft: '#9A958C',
    hair: '#2A2A32',
    accent: '#FF6B4A',
    accent2: '#57C4E5',
    accents: ['#FF6B4A', '#FFC857', '#57C4E5', '#B18CFF', '#5BD69B'],
    serif: "'Fraunces', Georgia, 'Times New Roman', serif",
    sans: "'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif",
  },
};
