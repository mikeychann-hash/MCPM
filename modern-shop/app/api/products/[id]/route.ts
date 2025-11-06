import { NextResponse } from 'next/server';
import { getProductById } from '@/lib/products';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const product = getProductById(params.id);

  if (!product) {
    return NextResponse.json({ message: 'Product not found' }, { status: 404 });
  }

  return NextResponse.json({ product });
}
