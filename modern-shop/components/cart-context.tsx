'use client';

import { createContext, useContext, useMemo, useState } from 'react';
import type { Product } from '@/lib/products';

export type CartItem = Product & { quantity: number };

type CartContextValue = {
  items: CartItem[];
  cartCount: number;
  total: number;
  addToCart: (product: Product) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  isOpen: boolean;
  toggleCart: () => void;
};

const CartContext = createContext<CartContextValue | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const value = useMemo<CartContextValue>(() => {
    const addToCart = (product: Product) => {
      setItems((prev) => {
        const existing = prev.find((item) => item.id === product.id);
        if (existing) {
          return prev.map((item) =>
            item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
          );
        }
        return [...prev, { ...product, quantity: 1 }];
      });
      setIsOpen(true);
    };

    const removeFromCart = (productId: string) => {
      setItems((prev) => prev.filter((item) => item.id !== productId));
    };

    const updateQuantity = (productId: string, quantity: number) => {
      setItems((prev) =>
        prev.map((item) => (item.id === productId ? { ...item, quantity: Math.max(1, quantity) } : item))
      );
    };

    const clearCart = () => setItems([]);

    const toggleCart = () => setIsOpen((prev) => !prev);

    const cartCount = items.reduce((acc, item) => acc + item.quantity, 0);
    const total = items.reduce((acc, item) => acc + item.quantity * item.price, 0);

    return {
      items,
      cartCount,
      total,
      addToCart,
      removeFromCart,
      updateQuantity,
      clearCart,
      isOpen,
      toggleCart
    };
  }, [items, isOpen]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used inside CartProvider');
  }
  return context;
}
