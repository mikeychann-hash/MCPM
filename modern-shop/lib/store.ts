import 'server-only';

import { cache } from 'react';
import { products, type Product } from '@/lib/products';

export const getProducts = cache(async () => {
  return products;
});

export const getFeaturedProducts = cache(async () => {
  return products.filter((product) => product.featured);
});

export const getProduct = cache(async (slug: string) => {
  return products.find((product) => product.slug === slug);
});

export type OrderPayload = {
  email: string;
  items: { id: string; quantity: number }[];
  address: {
    fullName: string;
    line1: string;
    city: string;
    country: string;
    postalCode: string;
  };
  paymentIntentId?: string;
};

export type Order = OrderPayload & {
  id: string;
  total: number;
  createdAt: string;
};

export const orders: Order[] = [];

export function createOrder(payload: OrderPayload): Order {
  const mappedItems: Product[] = [];
  let total = 0;

  payload.items.forEach((item) => {
    const product = products.find((p) => p.id === item.id);
    if (!product) {
      throw new Error(`Product ${item.id} not found`);
    }
    total += product.price * item.quantity;
    mappedItems.push(product);
  });

  const order: Order = {
    ...payload,
    id: `ord_${orders.length + 1}`,
    total,
    createdAt: new Date().toISOString()
  };

  orders.push(order);

  return order;
}
