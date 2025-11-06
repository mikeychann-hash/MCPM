const testimonials = [
  {
    quote: 'The attention to detail and premium materials make every purchase feel special. Our customers love the experience.',
    name: 'Adriana Holmes',
    title: 'Founder, Studio Sol'
  },
  {
    quote: 'We launched with Luna Commerce and never looked back. Beautiful defaults paired with exceptional performance.',
    name: 'Emile Warner',
    title: 'Head of Digital, North & Pine'
  },
  {
    quote: 'The admin tools keep our team focused on storytelling instead of spreadsheets. A dream for modern brands.',
    name: 'Rina Carter',
    title: 'Creative Director, Form Atelier'
  }
];

export function Testimonials() {
  return (
    <section className="container-fluid space-y-10">
      <header className="space-y-4">
        <p className="text-sm font-medium uppercase tracking-[0.4em] text-indigo-500">Trusted by design-led brands</p>
        <h2 className="section-title max-w-3xl">
          Built for teams that care deeply about craft and customer experience.
        </h2>
      </header>
      <div className="grid gap-6 md:grid-cols-3">
        {testimonials.map((testimonial) => (
          <blockquote key={testimonial.name} className="card space-y-6 text-left">
            <p className="text-base text-slate-600 dark:text-slate-300">“{testimonial.quote}”</p>
            <footer className="space-y-1 text-sm">
              <div className="font-semibold text-slate-900 dark:text-slate-100">{testimonial.name}</div>
              <div className="text-slate-500 dark:text-slate-400">{testimonial.title}</div>
            </footer>
          </blockquote>
        ))}
      </div>
    </section>
  );
}
