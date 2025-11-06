import { MetadataRoute } from 'next';
import { getProducts } from '@/lib/store';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://modern-shop.example';
  const products = await getProducts();

  const productEntries = products.map((product) => ({
    url: `${baseUrl}/products/${product.slug}`,
    lastModified: new Date().toISOString()
  }));

  return [
    { url: baseUrl, lastModified: new Date().toISOString() },
    { url: `${baseUrl}/products`, lastModified: new Date().toISOString() },
    { url: `${baseUrl}/cart`, lastModified: new Date().toISOString() },
    { url: `${baseUrl}/checkout`, lastModified: new Date().toISOString() },
    { url: `${baseUrl}/login`, lastModified: new Date().toISOString() },
    { url: `${baseUrl}/register`, lastModified: new Date().toISOString() },
    ...productEntries
  ];
}
