'use client';

import Link from 'next/link';
import { X } from '@lucide/react';
import { useCart } from '@/components/cart-context';

export default function CartDrawer() {
  const { items, total, isOpen, toggleCart, removeFromCart, updateQuantity } = useCart();

  return (
    <div
      className={`fixed inset-y-0 right-0 z-40 w-full max-w-md transform border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 dark:border-slate-800 dark:bg-slate-900 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex h-full flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-800">
          <h2 className="text-lg font-semibold">Your cart</h2>
          <button onClick={toggleCart} aria-label="Close cart" className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
          {items.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">You haven&apos;t added anything yet.</p>
          ) : (
            items.map((item) => (
              <div key={item.id} className="flex gap-4">
                <div
                  className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-2xl bg-slate-100"
                  style={{ backgroundImage: `url(${item.image})`, backgroundSize: 'cover' }}
                />
                <div className="flex flex-1 flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.name}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">${item.price.toFixed(2)}</p>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <button
                        className="h-7 w-7 rounded-full border border-slate-200 text-lg leading-none dark:border-slate-700"
                        onClick={() => updateQuantity(item.id, item.quantity - 1)}
                        aria-label="Decrease quantity"
                      >
                        -
                      </button>
                      <span className="w-8 text-center">{item.quantity}</span>
                      <button
                        className="h-7 w-7 rounded-full border border-slate-200 text-lg leading-none dark:border-slate-700"
                        onClick={() => updateQuantity(item.id, item.quantity + 1)}
                        aria-label="Increase quantity"
                      >
                        +
                      </button>
                    </div>
                    <button
                      className="text-slate-500 underline underline-offset-4 hover:text-indigo-500"
                      onClick={() => removeFromCart(item.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        <footer className="border-t border-slate-200 px-6 py-6 text-sm dark:border-slate-800">
          <div className="flex items-center justify-between text-base font-semibold text-slate-900 dark:text-slate-100">
            <span>Total</span>
            <span>${total.toFixed(2)}</span>
          </div>
          <div className="mt-4 flex flex-col gap-3">
            <Link href="/checkout" onClick={toggleCart} className="btn-primary text-center">
              Checkout
            </Link>
            <button onClick={toggleCart} className="btn-secondary">
              Continue shopping
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
