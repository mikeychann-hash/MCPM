'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message ?? 'Unable to sign in');
      }

      setMessage('Welcome back! Redirecting…');
      setTimeout(() => router.push('/dashboard/products'), 1200);
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
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Sign in</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Access the dashboard to manage your catalog and orders.</p>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <label>
            Email
            <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="btn-primary w-full" type="submit" disabled={isLoading}>
            {isLoading ? 'Signing in…' : 'Sign in'}
          </button>
          {message && <p className="text-sm text-slate-500 dark:text-slate-300">{message}</p>}
        </form>
        <p className="text-center text-xs text-slate-500 dark:text-slate-400">
          New to Luna Commerce?{' '}
          <a href="/register" className="text-indigo-500">
            Create an account
          </a>
        </p>
      </div>
    </section>
  );
}
