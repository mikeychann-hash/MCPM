'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useCart } from '@/components/cart-context';
import type { Product } from '@/lib/products';

export function ProductCard({ product }: { product: Product }) {
  const { addToCart } = useCart();

  return (
    <motion.article
      layout
      whileHover={{ y: -8 }}
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-lg transition dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="relative aspect-square overflow-hidden">
        <Image
          src={product.image}
          alt={product.name}
          fill
          className="object-cover transition duration-500 group-hover:scale-105"
        />
      </div>
      <div className="flex flex-1 flex-col gap-4 p-6">
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            <Link href={`/products/${product.slug}`}>{product.name}</Link>
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">{product.subtitle}</p>
        </div>
        <div className="mt-auto flex items-center justify-between">
          <span className="text-lg font-semibold text-slate-900 dark:text-slate-100">${product.price.toFixed(2)}</span>
          <button className="btn-secondary" onClick={() => addToCart(product)}>
            Add to cart
          </button>
        </div>
      </div>
    </motion.article>
  );
}
