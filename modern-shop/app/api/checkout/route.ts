import { NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createOrder, type OrderPayload } from '@/lib/store';

const stripeSecret = process.env.STRIPE_SECRET_KEY;

const stripe = stripeSecret
  ? new Stripe(stripeSecret, {
      apiVersion: '2023-10-16'
    })
  : null;

export async function POST(request: Request) {
  const payload = (await request.json()) as OrderPayload;

  if (!payload.email || payload.items.length === 0) {
    return NextResponse.json({ message: 'Missing order details' }, { status: 400 });
  }

  try {
    const order = createOrder(payload);

    if (stripe) {
      const paymentIntent = await stripe.paymentIntents.create({
        amount: Math.round(order.total * 100),
        currency: 'usd',
        receipt_email: payload.email,
        metadata: {
          orderId: order.id
        },
        automatic_payment_methods: {
          enabled: true
        }
      });

      return NextResponse.json({ order, clientSecret: paymentIntent.client_secret });
    }

    return NextResponse.json({ order, message: 'Stripe not configured. Order stored locally.' });
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : 'Checkout failed' }, { status: 400 });
  }
}
