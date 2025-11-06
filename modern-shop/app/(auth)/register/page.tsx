'use client';

import { useState } from 'react';

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', password: '', name: '' });
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message ?? 'Unable to create account');
      }

      setMessage('Account created! You can now sign in.');
      setForm({ email: '', password: '', name: '' });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="container-fluid flex min-h-[60vh] items-center justify-center">
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-slate-200 p-10 shadow-xl dark:border-slate-800">
        <div className="space-y-3 text-center">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Create your account</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Join the Luna Commerce community and start building your store.</p>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <label>
            Full name
            <input
              type="text"
              required
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              required
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            />
          </label>
          <button className="btn-primary w-full" type="submit" disabled={isLoading}>
            {isLoading ? 'Creating…' : 'Create account'}
          </button>
          {message && <p className="text-sm text-slate-500 dark:text-slate-300">{message}</p>}
        </form>
        <p className="text-center text-xs text-slate-500 dark:text-slate-400">
          Already have an account?{' '}
          <a href="/login" className="text-indigo-500">
            Sign in
          </a>
        </p>
      </div>
    </section>
  );
}
