'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShoppingBag, CircleUserRound, Menu } from '@lucide/react';
import { useState } from 'react';
import ThemeToggle from '@/components/theme-toggle';
import { useCart } from '@/components/cart-context';

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/products', label: 'Shop' },
  { href: '/dashboard/products', label: 'Dashboard' }
];

export default function Navbar() {
  const pathname = usePathname();
  const { cartCount, toggleCart } = useCart();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/60 bg-white/70 backdrop-blur-lg transition dark:border-slate-800/70 dark:bg-slate-950/70">
      <nav className="container-fluid flex h-20 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="rounded-full bg-indigo-500 px-3 py-1 text-white">LC</span>
          <span className="hidden sm:block">Luna Commerce</span>
        </Link>
        <div className="hidden items-center gap-8 text-sm font-medium md:flex">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`transition hover:text-indigo-500 ${pathname === item.href ? 'text-indigo-500' : 'text-slate-600 dark:text-slate-300'}`}
            >
              {item.label}
            </Link>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <button
            onClick={toggleCart}
            className="relative flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 transition hover:-translate-y-1 hover:shadow-lg dark:border-slate-700"
            aria-label="Open cart"
          >
            <ShoppingBag className="h-5 w-5" />
            {cartCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-semibold text-white">
                {cartCount}
              </span>
            )}
          </button>
          <Link
            href="/login"
            className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 transition hover:-translate-y-1 hover:shadow-lg dark:border-slate-700"
            aria-label="Account"
          >
            <CircleUserRound className="h-5 w-5" />
          </Link>
          <button
            className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 transition hover:-translate-y-1 hover:shadow-lg md:hidden dark:border-slate-700"
            onClick={() => setMenuOpen((prev) => !prev)}
            aria-label="Toggle menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </nav>
      {menuOpen && (
        <div className="border-t border-slate-200 bg-white px-6 py-4 shadow-lg dark:border-slate-700 dark:bg-slate-900 md:hidden">
          <div className="flex flex-col gap-4">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className="text-sm font-medium text-slate-600 dark:text-slate-200">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
