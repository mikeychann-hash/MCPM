import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from '@/app/providers';
import Navbar from '@/components/navbar';
import Footer from '@/components/footer';
import CartDrawer from '@/components/cart-drawer';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://modern-shop.example'),
  title: {
    default: 'Luna Commerce',
    template: '%s | Luna Commerce'
  },
  description: 'A modern, minimalist e-commerce experience built with Next.js and Tailwind CSS.',
  keywords: ['ecommerce', 'nextjs', 'tailwind', 'commerce', 'modern'],
  openGraph: {
    type: 'website',
    title: 'Luna Commerce',
    description: 'An elegant, high-performance storefront template.',
    url: process.env.NEXT_PUBLIC_SITE_URL ?? 'https://modern-shop.example',
    siteName: 'Luna Commerce'
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Luna Commerce',
    description: 'An elegant, high-performance storefront template.'
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} min-h-screen bg-slate-50 antialiased transition-colors dark:bg-slate-950`}>
        <Providers>
          <Navbar />
          <main className="flex-1 pb-24 pt-28">{children}</main>
          <CartDrawer />
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
