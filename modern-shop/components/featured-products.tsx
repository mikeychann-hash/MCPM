'use client';

import useSWR from 'swr';
import { ProductCard } from '@/components/product-card';
import type { Product } from '@/lib/products';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function FeaturedProducts() {
  const { data, error } = useSWR<{ products: Product[] }>('/api/products?featured=true', fetcher);

  if (error) {
    return <div className="text-sm text-red-500">Unable to load products.</div>;
  }

  if (!data) {
    return <div className="text-sm text-slate-500">Loading curated picks…</div>;
  }

  return (
    <div className="grid gap-8 sm:grid-cols-2 xl:grid-cols-3">
      {data.products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
