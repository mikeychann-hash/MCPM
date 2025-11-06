import Link from 'next/link';
import { FeaturedProducts } from '@/components/featured-products';
import { Hero } from '@/components/hero';
import { Testimonials } from '@/components/testimonials';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Home'
};

export default function HomePage() {
  return (
    <div className="space-y-32">
      <Hero />
      <section className="container-fluid space-y-12">
        <header className="flex items-center justify-between">
          <h2 className="section-title">Featured Arrivals</h2>
          <Link className="btn-secondary" href="/products">
            Explore catalog
          </Link>
        </header>
        <FeaturedProducts />
      </section>
      <Testimonials />
      <section className="container-fluid rounded-3xl bg-slate-900 py-16 text-slate-50 shadow-xl dark:bg-slate-800">
        <div className="mx-auto flex max-w-4xl flex-col gap-6 text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Stay in the know</h2>
          <p className="text-base text-slate-300">
            Subscribe to curated stories on the latest product drops and editorial content tailored to your style.
          </p>
          <form className="mx-auto flex w-full max-w-md flex-col gap-4 sm:flex-row">
            <input type="email" placeholder="Email address" required className="flex-1" />
            <button className="btn-primary" type="submit">
              Subscribe
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
