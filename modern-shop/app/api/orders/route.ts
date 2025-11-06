import { NextResponse } from 'next/server';
import { createOrder, orders, type OrderPayload } from '@/lib/store';

export async function GET() {
  return NextResponse.json({ orders });
}

export async function POST(request: Request) {
  const payload = (await request.json()) as OrderPayload;

  try {
    const order = createOrder(payload);
    return NextResponse.json({ order }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : 'Invalid order' }, { status: 400 });
  }
}
