import { Metadata } from 'next';
import { Suspense } from 'react';
import { ProductGrid } from '@/components/product-grid';

export const metadata: Metadata = {
  title: 'Shop'
};

export default function ProductsPage() {
  return (
    <section className="container-fluid space-y-12">
      <header className="space-y-4 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-indigo-500">Shop</p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Discover everyday essentials reimagined for modern living.
        </h1>
        <p className="mx-auto max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          Seamlessly manage your shopping experience with curated categories, refined search, and immersive product storytelling.
        </p>
      </header>
      <Suspense fallback={<div className="text-sm text-slate-500">Loading catalog…</div>}>
        <ProductGrid />
      </Suspense>
    </section>
  );
}
