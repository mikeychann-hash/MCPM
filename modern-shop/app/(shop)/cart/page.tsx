'use client';

import Link from 'next/link';
import { useCart } from '@/components/cart-context';

export default function CartPage() {
  const { items, total, removeFromCart, updateQuantity } = useCart();

  return (
    <section className="container-fluid space-y-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Shopping cart</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Review your selected pieces and complete checkout when you&apos;re ready.
        </p>
      </header>
      <div className="grid gap-12 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          {items.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Your cart is empty. Discover new favorites in our{' '}
              <Link href="/products" className="text-indigo-500">
                catalog
              </Link>
              .
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="flex items-center gap-6 rounded-3xl border border-slate-200 p-6 dark:border-slate-800">
                <div
                  className="h-32 w-32 flex-shrink-0 overflow-hidden rounded-2xl bg-slate-100"
                  style={{ backgroundImage: `url(${item.image})`, backgroundSize: 'cover' }}
                />
                <div className="flex flex-1 flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{item.name}</h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400">${item.price.toFixed(2)}</p>
                    </div>
                    <button className="text-sm text-slate-500 underline underline-offset-4 hover:text-indigo-500" onClick={() => removeFromCart(item.id)}>
                      Remove
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-slate-500">Quantity</span>
                    <div className="flex items-center rounded-full border border-slate-200 dark:border-slate-700">
                      <button className="px-3 py-2 text-sm" onClick={() => updateQuantity(item.id, item.quantity - 1)}>
                        -
                      </button>
                      <span className="w-10 text-center text-sm">{item.quantity}</span>
                      <button className="px-3 py-2 text-sm" onClick={() => updateQuantity(item.id, item.quantity + 1)}>
                        +
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        <aside className="space-y-6 rounded-3xl border border-slate-200 p-6 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Order summary</h2>
          <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
            <span>Subtotal</span>
            <span>${total.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
            <span>Shipping</span>
            <span>Calculated at checkout</span>
          </div>
          <div className="flex items-center justify-between text-base font-semibold text-slate-900 dark:text-slate-100">
            <span>Total</span>
            <span>${total.toFixed(2)}</span>
          </div>
          <Link href="/checkout" className="btn-primary block text-center">
            Proceed to checkout
          </Link>
        </aside>
      </div>
    </section>
  );
}
