import Link from 'next/link';
import Image from 'next/image';

export function Hero() {
  return (
    <section className="container-fluid grid gap-16 pb-20 pt-12 md:grid-cols-2 md:items-center">
      <div className="space-y-8">
        <span className="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1 text-xs font-medium tracking-wide text-indigo-500">
          Limited collection
        </span>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl dark:text-slate-100">
          Elevated essentials for the modern creative.
        </h1>
        <p className="max-w-xl text-base text-slate-600 dark:text-slate-300">
          Discover a curated line of sustainable goods crafted with premium materials and a minimalist aesthetic. Built to last and designed to inspire.
        </p>
        <div className="flex flex-col gap-4 sm:flex-row">
          <Link href="/products" className="btn-primary">
            Shop the collection
          </Link>
          <Link href="/about" className="btn-secondary">
            Read our story
          </Link>
        </div>
      </div>
      <div className="relative">
        <div className="absolute -inset-6 rounded-3xl bg-gradient-to-tr from-indigo-500/20 via-transparent to-slate-100 blur-2xl dark:from-indigo-400/20 dark:to-slate-900" />
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-50 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
          <Image
            src="https://images.unsplash.com/photo-1522312346375-d1a52e2b99b3?auto=format&fit=crop&w=1200&q=80"
            alt="Editorial showcase"
            width={1200}
            height={800}
            className="h-full w-full object-cover"
            priority
          />
        </div>
      </div>
    </section>
  );
}
