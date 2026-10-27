import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Running Coach',
  description: 'Générez des plans d\'entraînement personnalisés avec l\'IA',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
