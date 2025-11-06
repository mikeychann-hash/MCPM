'use client';

import { useTheme } from 'next-themes';
import { MoonStar, Sun } from '@lucide/react';
import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  const isDark = resolvedTheme === 'dark';

  return (
    <button
      className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 transition hover:-translate-y-1 hover:shadow-lg dark:border-slate-700"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
    </button>
  );
}
