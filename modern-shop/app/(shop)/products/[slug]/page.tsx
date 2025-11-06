import Image from 'next/image';
import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import { getProduct } from '@/lib/store';
import { Suspense } from 'react';
import { ProductRecommendations } from '@/components/product-recommendations';
import { AddToCartButton } from '@/components/add-to-cart-button';

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const product = await getProduct(params.slug);

  if (!product) {
    return {
      title: 'Product not found'
    };
  }

  return {
    title: product.name,
    description: product.description,
    openGraph: {
      title: product.name,
      description: product.description,
      images: [product.image]
    }
  };
}

export default async function ProductPage({ params }: { params: { slug: string } }) {
  const product = await getProduct(params.slug);

  if (!product) {
    notFound();
  }

  return (
    <section className="container-fluid grid gap-12 lg:grid-cols-2 lg:items-start">
      <div className="grid gap-4">
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-50 shadow-xl dark:border-slate-800 dark:bg-slate-900">
          <Image
            src={product.image}
            alt={product.name}
            width={1200}
            height={1200}
            className="h-full w-full object-cover"
            priority
          />
        </div>
      </div>
      <div className="space-y-8">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.4em] text-indigo-500">{product.category}</p>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{product.name}</h1>
          <p className="text-base text-slate-500 dark:text-slate-300">{product.subtitle}</p>
        </div>
        <div className="text-2xl font-semibold text-slate-900 dark:text-slate-100">${product.price.toFixed(2)}</div>
        <p className="text-sm text-slate-600 dark:text-slate-300">{product.description}</p>
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Color</h3>
            <div className="flex flex-wrap gap-2">
              {product.colors.map((color) => (
                <button key={color} className="rounded-full border border-slate-200 px-4 py-2 text-xs uppercase tracking-wide text-slate-600 transition hover:border-indigo-500 hover:text-indigo-500 dark:border-slate-700 dark:text-slate-300">
                  {color}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Size</h3>
            <div className="flex flex-wrap gap-2">
              {product.sizes.map((size) => (
                <button key={size} className="rounded-full border border-slate-200 px-4 py-2 text-xs uppercase tracking-wide text-slate-600 transition hover:border-indigo-500 hover:text-indigo-500 dark:border-slate-700 dark:text-slate-300">
                  {size}
                </button>
              ))}
            </div>
          </div>
        </div>
        <AddToCartButton product={product} />
        <div className="space-y-4 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
          <p>Free carbon-neutral shipping on orders over $200.</p>
          <p>Hassle-free returns within 30 days of delivery.</p>
        </div>
        <div className="space-y-6">
          <h2 className="section-title">You might also love</h2>
          <Suspense fallback={<div className="text-sm text-slate-500">Loading recommendations…</div>}>
            <ProductRecommendations currentProductId={product.id} />
          </Suspense>
        </div>
      </div>
    </section>
  );
}
