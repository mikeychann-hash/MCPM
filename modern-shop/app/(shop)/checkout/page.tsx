'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/components/cart-context';

const initialForm = {
  email: '',
  fullName: '',
  line1: '',
  city: '',
  country: '',
  postalCode: ''
};

export default function CheckoutPage() {
  const { items, total, clearCart } = useCart();
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (items.length === 0) {
      setMessage('Add products to your cart before checking out.');
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: form.email,
          address: {
            fullName: form.fullName,
            line1: form.line1,
            city: form.city,
            country: form.country,
            postalCode: form.postalCode
          },
          items: items.map((item) => ({ id: item.id, quantity: item.quantity }))
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message ?? 'Unable to process checkout');
      }

      setMessage('Order confirmed! A receipt has been sent to your inbox.');
      clearCart();
      setForm(initialForm);
      setTimeout(() => router.push('/'), 1200);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unexpected error.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="container-fluid grid gap-12 lg:grid-cols-[2fr_1fr]">
      <div className="space-y-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Checkout</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Securely complete your order with encrypted payment processing.
          </p>
        </header>
        <form className="space-y-8" onSubmit={handleSubmit}>
          <fieldset className="grid gap-6 rounded-3xl border border-slate-200 p-6 dark:border-slate-800">
            <legend className="text-sm font-semibold uppercase tracking-[0.3em] text-indigo-500">Contact</legend>
            <label>
              Email
              <input
                type="email"
                required
                value={form.email}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              />
            </label>
          </fieldset>
          <fieldset className="grid gap-6 rounded-3xl border border-slate-200 p-6 dark:border-slate-800">
            <legend className="text-sm font-semibold uppercase tracking-[0.3em] text-indigo-500">Shipping address</legend>
            <label>
              Full name
              <input
                type="text"
                required
                value={form.fullName}
                onChange={(event) => setForm((prev) => ({ ...prev, fullName: event.target.value }))}
              />
            </label>
            <label>
              Address line
              <input
                type="text"
                required
                value={form.line1}
                onChange={(event) => setForm((prev) => ({ ...prev, line1: event.target.value }))}
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label>
                City
                <input
                  type="text"
                  required
                  value={form.city}
                  onChange={(event) => setForm((prev) => ({ ...prev, city: event.target.value }))}
                />
              </label>
              <label>
                Country
                <input
                  type="text"
                  required
                  value={form.country}
                  onChange={(event) => setForm((prev) => ({ ...prev, country: event.target.value }))}
                />
              </label>
            </div>
            <label>
              Postal code
              <input
                type="text"
                required
                value={form.postalCode}
                onChange={(event) => setForm((prev) => ({ ...prev, postalCode: event.target.value }))}
              />
            </label>
          </fieldset>
          <button className="btn-primary" type="submit" disabled={isLoading}>
            {isLoading ? 'Processing…' : 'Complete order'}
          </button>
          {message && <p className="text-sm text-slate-500 dark:text-slate-300">{message}</p>}
        </form>
      </div>
      <aside className="space-y-6 rounded-3xl border border-slate-200 p-6 text-sm dark:border-slate-800 dark:text-slate-300">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Order summary</h2>
        <ul className="space-y-4">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between">
              <span>
                {item.name} × {item.quantity}
              </span>
              <span>${(item.quantity * item.price).toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between text-base font-semibold text-slate-900 dark:text-slate-100">
          <span>Total</span>
          <span>${total.toFixed(2)}</span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Payments are securely processed by Stripe. Update <code>.env</code> with your API keys before deploying.
        </p>
      </aside>
    </section>
  );
}
