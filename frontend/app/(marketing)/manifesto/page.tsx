export default function ManifestoPage() {
  return (
    <article className="mx-auto max-w-2xl px-6 py-24 md:py-32">
      <p className="text-[11px] uppercase tracking-[0.35em] text-gold">Manifesto</p>
      <h1 className="mt-6 font-display text-6xl leading-[1] md:text-7xl">
        Every voice belongs to its <em className="text-gold">maker.</em>
      </h1>

      <div className="mt-14 space-y-8 text-lg leading-[1.75] text-foreground/90">
        <p className="font-display text-2xl italic leading-[1.4] text-gold">
          Every other AI creative tool assumes you already know what you want to make.
        </p>
        <p>
          You open a blank prompt box, and the tool waits. It presumes taste. It presumes
          direction. It presumes that the hard part is producing pixels or words &mdash; and it
          solves that.
        </p>
        <p>
          But the hard part isn&apos;t production. The hard part is <em>consistency</em>. Making the
          next thing feel like the last thing without repeating yourself. Knowing what your
          voice is when you&apos;ve never had to describe it out loud.
        </p>

        <div className="gold-rule my-14" />

        <h2 className="font-display text-4xl">A different starting question.</h2>
        <p>
          StyleSync doesn&apos;t ask you what you want to make. It asks the opposite: who are you
          already, and how do you make more of that?
        </p>
        <p>
          The answer is already in your feed. A hundred posts, a hundred small decisions about
          what to write, what to show, when to be quiet. That&apos;s a brand voice. It&apos;s just never
          been written down.
        </p>

        <div className="gold-rule my-14" />

        <h2 className="font-display text-4xl">Why Granite. Why local.</h2>
        <p>
          IBM Granite 3.1 is small enough to run on a laptop and capable enough to do
          fourteen coordinated things well: brand extraction, generation, diagnosis, strategy.
          That combination &mdash; small, capable, local &mdash; is what makes creator-owned AI
          possible at all.
        </p>
        <p>
          Nothing leaves the room. Not your captions, not your metrics, not your voice. If your
          AI creative tool sends your work to somebody else&apos;s server, it isn&apos;t your tool.
        </p>

        <div className="gold-rule my-14" />

        <h2 className="font-display text-4xl">The unfair advantage.</h2>
        <p>
          You&apos;ve already made a thousand decisions. StyleSync just remembers all of them, and
          helps you make the next one.
        </p>
      </div>

      <p className="mt-20 font-mono text-xs text-muted-foreground">
        &mdash; Zaid Shaikh, Northeastern University &middot; July 2026
      </p>
    </article>
  );
}
