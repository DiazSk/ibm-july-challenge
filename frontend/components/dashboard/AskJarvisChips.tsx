"use client";

// Tappable prompt chips that open the Jarvis widget pre-filled with an
// insight question. JarvisWidget listens for the "jarvis:ask" window event.
const QUESTIONS = [
  "Which pillar gets the most saves?",
  "When's my best time to post?",
  "Which post performed best and why?",
  "What's my average engagement rate?",
];

export default function AskJarvisChips() {
  function ask(q: string) {
    window.dispatchEvent(new CustomEvent("jarvis:ask", { detail: q }));
  }

  return (
    <div className="flex flex-wrap gap-2">
      {QUESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => ask(q)}
          className="text-[11px] px-3 py-1.5 rounded-full border transition-colors hover:opacity-80"
          style={{
            borderColor: "var(--color-ql-border)",
            color: "var(--color-ql-dark)",
            background: "var(--color-ql-card)",
          }}
        >
          {q}
        </button>
      ))}
    </div>
  );
}
