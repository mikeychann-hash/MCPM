import { getProducts } from '@/lib/store';
import { ProductCard } from '@/components/product-card';

export async function ProductRecommendations({ currentProductId }: { currentProductId: string }) {
  const products = await getProducts();
  const recommendations = products.filter((product) => product.id !== currentProductId).slice(0, 3);

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {recommendations.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
