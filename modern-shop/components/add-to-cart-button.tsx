'use client';

import { useCart } from '@/components/cart-context';
import type { Product } from '@/lib/products';

export function AddToCartButton({ product }: { product: Product }) {
  const { addToCart } = useCart();

  return (
    <button className="btn-primary w-full sm:w-auto" onClick={() => addToCart(product)}>
      Add to cart
    </button>
  );
}
