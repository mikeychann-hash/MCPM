import { ProductCard } from '@/components/product-card';
import { getProducts } from '@/lib/store';

export async function ProductGrid() {
  const products = await getProducts();

  return (
    <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
