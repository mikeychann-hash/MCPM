export type Product = {
  id: string;
  name: string;
  slug: string;
  price: number;
  subtitle: string;
  description: string;
  image: string;
  category: string;
  colors: string[];
  sizes: string[];
  featured?: boolean;
  inventory: number;
};

export const products: Product[] = [
  {
    id: '1',
    name: 'Atlas Merino Crew',
    slug: 'atlas-merino-crew',
    price: 168,
    subtitle: 'Soft-touch merino wool knit',
    description:
      'A lightweight merino crew made with ethically sourced fibers, designed to layer beautifully for year-round comfort.',
    image: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=1200&q=80',
    category: 'Apparel',
    colors: ['Charcoal', 'Ivory', 'Cedar'],
    sizes: ['XS', 'S', 'M', 'L', 'XL'],
    featured: true,
    inventory: 24
  },
  {
    id: '2',
    name: 'Contour Leather Tote',
    slug: 'contour-leather-tote',
    price: 220,
    subtitle: 'Vegetable-tanned Italian leather',
    description:
      'Handcrafted with precision, the Contour Tote balances sculptural lines with everyday utility. Includes a removable tech sleeve.',
    image: 'https://images.unsplash.com/photo-1514996937319-344454492b37?auto=format&fit=crop&w=1200&q=80',
    category: 'Accessories',
    colors: ['Umber', 'Midnight'],
    sizes: ['One size'],
    featured: true,
    inventory: 15
  },
  {
    id: '3',
    name: 'Eclipse Ceramic Set',
    slug: 'eclipse-ceramic-set',
    price: 142,
    subtitle: 'Hand-thrown matte glaze',
    description:
      'Elevate your dining with a four-piece ceramic set featuring subtle gradients inspired by lunar phases. Oven and dishwasher safe.',
    image: 'https://images.unsplash.com/photo-1488900128323-21503983a07e?auto=format&fit=crop&w=1200&q=80',
    category: 'Home',
    colors: ['Graphite', 'Pearl'],
    sizes: ['Set of 4'],
    featured: true,
    inventory: 32
  },
  {
    id: '4',
    name: 'Orbit Desk Lamp',
    slug: 'orbit-desk-lamp',
    price: 198,
    subtitle: 'Adjustable warm LED lighting',
    description:
      'Anodized aluminum and frosted glass combine for a sculptural lamp with adjustable brightness and ambient glow mode.',
    image: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1200&q=80',
    category: 'Lighting',
    colors: ['Brushed Steel', 'Onyx'],
    sizes: ['One size'],
    inventory: 12
  },
  {
    id: '5',
    name: 'Lumen Minimal Watch',
    slug: 'lumen-minimal-watch',
    price: 248,
    subtitle: 'Swiss quartz with sapphire crystal',
    description:
      'Precision and simplicity with luminous indices, a scratch-resistant sapphire crystal, and interchangeable straps.',
    image: 'https://images.unsplash.com/photo-1524594154908-edd0b7e89c4f?auto=format&fit=crop&w=1200&q=80',
    category: 'Accessories',
    colors: ['Midnight', 'Sandstone'],
    sizes: ['38mm', '42mm'],
    inventory: 20
  },
  {
    id: '6',
    name: 'Aria Linen Duvet',
    slug: 'aria-linen-duvet',
    price: 286,
    subtitle: 'Breathable Belgian linen',
    description:
      'Washed linen duvet set with a lived-in softness that keeps you cool through warmer months and cozy in cooler seasons.',
    image: 'https://images.unsplash.com/photo-1505692794403-55b39e8e0c76?auto=format&fit=crop&w=1200&q=80',
    category: 'Home',
    colors: ['Fog', 'Clay', 'Cloud'],
    sizes: ['Full/Queen', 'King'],
    inventory: 18
  }
];

export function getProductBySlug(slug: string) {
  return products.find((product) => product.slug === slug);
}

export function getProductById(id: string) {
  return products.find((product) => product.id === id);
}
