import { getProducts } from '@/lib/store';

export async function ProductTable() {
  const products = await getProducts();

  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 shadow-sm dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr className="text-left text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
            <th className="px-6 py-4">Product</th>
            <th className="px-6 py-4">Inventory</th>
            <th className="px-6 py-4">Price</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4" aria-label="Actions" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white text-sm dark:divide-slate-800 dark:bg-slate-950">
          {products.map((product) => (
            <tr key={product.id} className="transition hover:bg-slate-50/60 dark:hover:bg-slate-900/60">
              <td className="px-6 py-4">
                <div className="space-y-1">
                  <p className="font-medium text-slate-900 dark:text-slate-100">{product.name}</p>
                  <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{product.category}</p>
                </div>
              </td>
              <td className="px-6 py-4 text-slate-600 dark:text-slate-300">{product.inventory}</td>
              <td className="px-6 py-4 text-slate-600 dark:text-slate-300">${product.price.toFixed(2)}</td>
              <td className="px-6 py-4">
                <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400">
                  Active
                </span>
              </td>
              <td className="px-6 py-4 text-right">
                <button className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
                  Edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
