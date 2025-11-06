import { NextResponse } from 'next/server';
import { getProducts, getFeaturedProducts } from '@/lib/store';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const featuredOnly = searchParams.get('featured');

  const products = featuredOnly ? await getFeaturedProducts() : await getProducts();

  return NextResponse.json({ products });
}
