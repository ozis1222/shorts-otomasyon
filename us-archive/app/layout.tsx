import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'The Us Archive — Your relationship, decoded.',
  description:
    'Turn years of conversations into a one-of-a-kind digital archive: a premium magazine, a generative relationship fingerprint, and shareable cards.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
