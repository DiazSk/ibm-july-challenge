const stages = [
  {
    n: "01",
    name: "Ingest",
    tag: "Instaloader",
    body:
      "StyleSync pulls the last 100+ posts from your public Instagram: captions, image URLs, engagement metrics, and average watch time.",
    detail:
      "Nothing you didn't already publish. The scrape is one-time and cached locally as JSON.",
  },
  {
    n: "02",
    name: "Embed",
    tag: "Local · Sentence-Transformers",
    body:
      "Every post gets an embedding — a dense vector that captures what the caption is about and how it sounds.",
    detail: "Embeddings run on-device. Nothing is sent to a third-party API, ever.",
  },
  {
    n: "03",
    name: "Cluster",
    tag: "K-Means",
    body:
      "Your embeddings are grouped into content pillars — the recurring territories your account already covers.",
    detail: "Pillars come from behavior, not self-description.",
  },
  {
    n: "04",
    name: "Profile",
    tag: "Granite #1",
    body:
      "Granite reads a stratified sample from each pillar and extracts tone descriptors, vocabulary, and brand guidelines.",
    detail: "This is the brand voice profile. Everything downstream inherits from it.",
  },
  {
    n: "05",
    name: "Generate",
    tag: "Granite #2, #3, #6, #7, #9, #12",
    body:
      "Caption generation, image direction prompts, blank-page creative directions, script generation, and voice refinement — all conditioned on the profile.",
    detail: "You give StyleSync a goal and a pillar. It gives you drafts in your voice.",
  },
  {
    n: "06",
    name: "Diagnose",
    tag: "Granite #4, #5, #8, #10, #11",
    body:
      "The Why Engine reads a post plus its metrics and explains what happened. Strategic Insights and Boost Advisor identify under- and over-invested pillars.",
    detail:
      "Not \"reach was low\" — but \"the opening line has no sensory anchor, which is where your top posts live.\"",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-24 md:py-32">
      <p className="text-[11px] uppercase tracking-[0.35em] text-gold">Pipeline</p>
      <h1 className="mt-6 font-display text-6xl leading-[1] md:text-7xl">How StyleSync works.</h1>
      <p className="mt-8 max-w-2xl text-lg leading-relaxed text-muted-foreground">
        Six stages. Fourteen Granite calls. Zero cloud AI at inference. This is the full pipeline
        from your public Instagram archive to a living brand voice profile you can use.
      </p>

      <div className="mt-20 space-y-16">
        {stages.map((s) => (
          <article key={s.n} className="grid gap-6 md:grid-cols-[100px_1fr]">
            <div>
              <p className="font-mono text-sm text-gold">{s.n}</p>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">{s.tag}</p>
            </div>
            <div>
              <h2 className="font-display text-4xl">{s.name}</h2>
              <p className="mt-3 text-base leading-relaxed text-foreground/90">{s.body}</p>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{s.detail}</p>
              <div className="mt-6 gold-rule" />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
