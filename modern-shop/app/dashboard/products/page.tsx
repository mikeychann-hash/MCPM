import { Metadata } from 'next';
import { ProductTable } from '@/components/product-table';

export const metadata: Metadata = {
  title: 'Dashboard'
};

export default function DashboardProductsPage() {
  return (
    <section className="container-fluid space-y-12">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Product management</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Review inventory, adjust pricing, and manage visibility for each product.
          </p>
        </div>
        <button className="btn-primary">Add product</button>
      </header>
      <ProductTable />
    </section>
  );
}
