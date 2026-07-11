import Link from "next/link";

const tiers = [
  {
    name: "Solo",
    price: "$0",
    cadence: "forever",
    tagline: "One brand voice profile. Everything local.",
    features: [
      "1 Instagram brand",
      "Full 6-stage pipeline",
      "Unlimited local generations",
      "Why Engine diagnosis",
      "Runs on your laptop",
    ],
    cta: "Get started",
    featured: false,
  },
  {
    name: "Studio",
    price: "$24",
    cadence: "per month",
    tagline: "For creators running multiple properties.",
    features: [
      "Up to 5 brand voices",
      "Strategic Insights briefing",
      "Blank Page Solver + Script Studio",
      "Boost Advisor",
      "Priority Granite scheduling",
    ],
    cta: "Start Studio",
    featured: true,
  },
  {
    name: "Agency",
    price: "Custom",
    cadence: "annual",
    tagline: "For teams managing creator rosters.",
    features: [
      "Unlimited brands",
      "Team seats & handoff",
      "White-labeled briefs",
      "On-prem deployment",
      "Priority engineering support",
    ],
    cta: "Talk to us",
    featured: false,
  },
];

export default function PricingPage() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 md:py-32">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-[11px] uppercase tracking-[0.35em] text-gold">Pricing</p>
        <h1 className="mt-6 font-display text-6xl leading-[1] md:text-7xl">Priced for the maker.</h1>
        <p className="mt-6 text-muted-foreground">
          Free for individuals. Everything runs locally, so your marginal cost is your electricity.
        </p>
      </div>

      <div className="mt-16 grid gap-6 md:grid-cols-3">
        {tiers.map((t) => (
          <div
            key={t.name}
            className={`hairline rounded-md p-8 ${
              t.featured ? "border-gold/40 bg-gradient-to-b from-gold/10 to-transparent" : "bg-card"
            }`}
          >
            <div className="flex items-baseline justify-between">
              <p className="font-display text-2xl">{t.name}</p>
              {t.featured && (
                <span className="rounded-sm bg-gold/20 px-2 py-0.5 text-[10px] uppercase tracking-widest text-gold">
                  Most picked
                </span>
              )}
            </div>
            <div className="mt-6 flex items-baseline gap-2">
              <p className="font-display text-6xl text-foreground">{t.price}</p>
              <p className="text-sm text-muted-foreground">/ {t.cadence}</p>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{t.tagline}</p>
            <div className="my-6 gold-rule" />
            <ul className="space-y-3 text-sm">
              {t.features.map((f) => (
                <li key={f} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-gold" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/app"
              className={`mt-8 inline-flex w-full items-center justify-center rounded-sm px-4 py-2.5 text-sm font-medium transition ${
                t.featured
                  ? "bg-primary text-primary-foreground hover:opacity-90"
                  : "border border-border text-foreground hover:bg-secondary"
              }`}
            >
              {t.cta}
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
