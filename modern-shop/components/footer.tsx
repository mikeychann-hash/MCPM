import Link from 'next/link';

const footerLinks = [
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Sustainability', href: '#' },
      { label: 'Careers', href: '#' }
    ]
  },
  {
    title: 'Support',
    links: [
      { label: 'Help center', href: '#' },
      { label: 'Shipping', href: '#' },
      { label: 'Returns', href: '#' }
    ]
  },
  {
    title: 'Resources',
    links: [
      { label: 'Journal', href: '#' },
      { label: 'Gift cards', href: '#' },
      { label: 'Affiliate', href: '#' }
    ]
  }
];

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white/60 py-16 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
      <div className="container-fluid grid gap-12 md:grid-cols-4">
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
            <span className="rounded-full bg-indigo-500 px-3 py-1 text-white">LC</span>
            Luna Commerce
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Crafted to help modern brands deliver elevated customer experiences with a refined, minimalist touch.
          </p>
        </div>
        {footerLinks.map((section) => (
          <div key={section.title} className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {section.title}
            </h3>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              {section.links.map((link) => (
                <li key={link.label}>
                  <Link className="transition hover:text-indigo-500" href={link.href}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="container-fluid mt-12 flex flex-col justify-between gap-6 border-t border-slate-200 pt-8 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400 md:flex-row">
        <p>© {new Date().getFullYear()} Luna Commerce. Crafted for modern retail experiences.</p>
        <div className="flex items-center gap-4">
          <Link href="#" className="hover:text-indigo-500">
            Privacy Policy
          </Link>
          <Link href="#" className="hover:text-indigo-500">
            Terms of Service
          </Link>
        </div>
      </div>
    </footer>
  );
}
