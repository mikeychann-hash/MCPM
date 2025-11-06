# Luna Commerce

Luna Commerce is a modern e-commerce template inspired by refined, minimalist retail experiences. It is built with Next.js 14, the App Router, TypeScript, and Tailwind CSS. The project showcases a full customer journey paired with an admin dashboard and API layer so you can ship a polished storefront quickly.

## ✨ Features

- **Responsive storefront** with product collections, hero storytelling, testimonials, and newsletter capture.
- **Dynamic product detail pages** featuring image zoom effects, color and size selectors, and related recommendations.
- **Persistent cart system** backed by React context with an animated drawer, cart page, and checkout summary.
- **Checkout workflow** that integrates with Stripe (via Payment Intents) and gracefully degrades when API keys are missing.
- **Authentication endpoints** for registering new accounts and validating admin credentials stored via environment variables.
- **Admin dashboard** that surfaces product inventory and pricing in a clean, accessible table layout.
- **SEO-ready** metadata, sitemap, robots rules, and Open Graph defaults.
- **Dark and light modes** powered by `next-themes` with a toggle in the global navigation.
- **Type-safe API layer** using the Next.js App Router and server utilities for product/order management.

## 🗂️ Project Structure

```
modern-shop/
├── app/
│   ├── (auth)/
│   ├── (shop)/
│   ├── api/
│   ├── dashboard/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── providers.tsx
│   ├── robots.ts
│   └── sitemap.ts
├── components/
├── lib/
├── public/
├── styles/
├── .env.example
├── next.config.mjs
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- pnpm, npm, or yarn

### Installation

```bash
pnpm install
pnpm dev
```

Or with npm:

```bash
npm install
npm run dev
```

Visit `http://localhost:3000` to explore the storefront.

### Environment variables

Copy `.env.example` to `.env.local` and update the values:

- `NEXT_PUBLIC_SITE_URL`: canonical site URL used for SEO metadata.
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: Stripe publishable key for client integrations.
- `STRIPE_SECRET_KEY`: Stripe secret key that enables real PaymentIntent creation during checkout.
- `ADMIN_EMAIL` & `ADMIN_PASSWORD`: credentials for the default admin account used by the login endpoint.

### Stripe integration

When `STRIPE_SECRET_KEY` is configured, the `/api/checkout` endpoint creates a Payment Intent and returns the client secret. Without keys, the order will still be stored in memory and the UI communicates that payments are mocked, making development workflows fast and safe.

### Scripts

- `pnpm dev` – start the local development server
- `pnpm build` – generate an optimized production build
- `pnpm start` – run the production server
- `pnpm lint` – run ESLint using Next.js defaults

## 🧱 Components & Styling

- Tailwind CSS powers the design system with semantic utility classes and helper components (`btn-primary`, `card`, etc.).
- Animations use `framer-motion` and CSS transitions to mirror the smooth, elevated interactions of premium storefronts.
- Global providers enable theme toggling, cart context, and data fetching via React Query.

## 🛠️ API Overview

- `GET /api/products` – list products (`?featured=true` for curated selections)
- `GET /api/products/[id]` – fetch a single product by ID
- `POST /api/orders` – create an order and capture structured address information
- `POST /api/checkout` – create an order and, when Stripe is configured, initiate payment
- `POST /api/auth/login` – authenticate against the in-memory user store (backed by env credentials)
- `POST /api/auth/register` – add a new user to the in-memory store

## 📦 Optional Docker

Create a production image with the included `Dockerfile` (see below) and deploy to your hosting provider of choice.

```bash
docker build -t luna-commerce .
docker run -p 3000:3000 luna-commerce
```

## 🧭 Roadmap ideas

- Replace in-memory storage with a persistent database (Prisma + PostgreSQL).
- Add order history and profile management to the account area.
- Integrate real-time inventory and webhook-driven order updates.

## 📝 License

Released as an open-source starter. Adapt it for commercial projects or internal tooling.
