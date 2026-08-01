"""
Profile audit — does the extracted brand vocabulary describe the account, or
does it just memorise it?

The Drift Test in src/generation/voice_fidelity.py awards points for reusing
terms from brand_profile.json. That is only a meaningful signal if those terms
are genuinely *recurring* patterns in the account's writing. If a "signature
phrase" is a verbatim copy of one past caption, then matching it means the model
reproduced a specific post — not that it captured a voice. If a "recurring word"
appears in one post out of ninety-six, it is not recurring.

This script measures both, with no LLM call and no generation. It reads the
shipped profile and the source captions it was extracted from, and reports:

  · for each signature phrase — is it a verbatim substring of a training caption?
  · for each recurring word   — how often does it actually appear?

Recurrence is reported against two different denominators, and the distinction
matters:

  "sample"  — the first MAX_POSTS_PER_CALL posts of the cluster, which is all
              BrandProfileExtractor._format_posts actually shows Granite. A term
              absent here was invented outright.
  "pillar"  — every post in the cluster. A term that looks frequent in the
              sample but is rare across the pillar was not invented, it simply
              does not generalise — and generation for the whole pillar is
              conditioned on it regardless.

Run:
    python eval/audit_profile.py
"""

import json
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"
REPORT_PATH = _PROJECT_ROOT / "eval" / "artifacts" / "profile_audit.json"

# Mirrors profile_extractor.MAX_POSTS_PER_CALL — the extractor's context cap, and
# therefore the real evidence base for every pillar's voice profile.
EXTRACTOR_SAMPLE_CAP = 12

# A term appearing in fewer than this share of posts is not usefully "recurring".
RECURRENCE_FLOOR = 0.10


def word_occurrences(term: str, captions: list[str]) -> int:
    """Whole-word count, matching the semantics of voice_fidelity._word_hits."""
    pattern = re.compile(rf"\b{re.escape(term.lower())}\b")
    return sum(1 for c in captions if pattern.search(c.lower()))


def audit(clusters: dict, profile: dict) -> dict:
    by_cluster = clusters["clusters"]
    findings = []

    for entry in profile["cluster_profiles"]:
        cid = str(entry["cluster_id"])
        prof = entry["profile"]
        captions = [p["marketing_hook"] for p in by_cluster.get(cid, [])]
        sample = captions[:EXTRACTOR_SAMPLE_CAP]
        blob = " || ".join(captions).lower()
        n, n_sample = len(captions), len(sample)

        vocab = prof.get("vocabulary_patterns", {})

        phrases = [
            {
                "phrase": s,
                "verbatim_in_training": s.lower() in blob,
            }
            for s in vocab.get("signature_phrases", [])
        ]

        words = []
        for w in vocab.get("recurring_words", []):
            hits_pillar = word_occurrences(w, captions)
            hits_sample = word_occurrences(w, sample)
            share_pillar = hits_pillar / n if n else 0.0
            share_sample = hits_sample / n_sample if n_sample else 0.0
            words.append({
                "word": w,
                "sample_occurrences": hits_sample,
                "sample_posts": n_sample,
                "sample_share": round(share_sample, 4),
                "pillar_occurrences": hits_pillar,
                "pillar_posts": n,
                "pillar_share": round(share_pillar, 4),
                # Absent from the evidence the extractor was shown: invented.
                "invented": hits_sample == 0,
                # Looked frequent in the sample, rare across the pillar it now
                # conditions generation for.
                "fails_to_generalise": (
                    hits_sample > 0
                    and share_sample >= RECURRENCE_FLOOR
                    and share_pillar < RECURRENCE_FLOOR
                ),
            })

        findings.append({
            "cluster_id": entry["cluster_id"],
            "content_pillar": prof.get("content_pillar"),
            "pillar_posts": n,
            "posts_shown_to_extractor": n_sample,
            "signature_phrases": phrases,
            "recurring_words": words,
        })

    all_phrases = [p for f in findings for p in f["signature_phrases"]]
    all_words = [w for f in findings for w in f["recurring_words"]]

    return {
        "recurrence_floor": RECURRENCE_FLOOR,
        "extractor_sample_cap": EXTRACTOR_SAMPLE_CAP,
        "summary": {
            "signature_phrases_total": len(all_phrases),
            "signature_phrases_verbatim": sum(
                1 for p in all_phrases if p["verbatim_in_training"]
            ),
            "recurring_words_total": len(all_words),
            "recurring_words_invented": sum(1 for w in all_words if w["invented"]),
            "recurring_words_fail_to_generalise": sum(
                1 for w in all_words if w["fails_to_generalise"]
            ),
            "pillar_posts_total": sum(f["pillar_posts"] for f in findings),
            "posts_shown_to_extractor_total": sum(
                f["posts_shown_to_extractor"] for f in findings
            ),
            "smallest_pillar_post_count": min(f["pillar_posts"] for f in findings),
        },
        "clusters": findings,
    }


def render(report: dict) -> None:
    s = report["summary"]
    print("── Signature phrases ─────────────────────────────────────────────")
    for f in report["clusters"]:
        for p in f["signature_phrases"]:
            mark = "VERBATIM" if p["verbatim_in_training"] else "derived "
            print(f"  [{mark}] c{f['cluster_id']}  {p['phrase']!r}")

    print("\n── Recurring words ───────────────────────────────────────────────")
    print("     sample = posts the extractor read · pillar = whole cluster")
    for f in report["clusters"]:
        print(f"\n  cluster {f['cluster_id']} · {f['content_pillar']} · "
              f"{f['posts_shown_to_extractor']} of {f['pillar_posts']} posts read")
        for w in sorted(f["recurring_words"], key=lambda x: x["pillar_share"]):
            if w["invented"]:
                flag = "  ← INVENTED (absent from what the extractor read)"
            elif w["fails_to_generalise"]:
                flag = "  ← does not generalise beyond the sample"
            else:
                flag = ""
            print(f"      sample {w['sample_occurrences']:>2}/{w['sample_posts']:<2} "
                  f"({w['sample_share']:>5.0%})   "
                  f"pillar {w['pillar_occurrences']:>3}/{w['pillar_posts']:<3} "
                  f"({w['pillar_share']:>5.1%})   {w['word']!r}{flag}")

    print("\n── Summary ───────────────────────────────────────────────────────")
    print(f"  signature phrases that are verbatim training captions: "
          f"{s['signature_phrases_verbatim']}/{s['signature_phrases_total']}")
    print(f"  'recurring' words invented outright:                   "
          f"{s['recurring_words_invented']}/{s['recurring_words_total']}")
    print(f"  'recurring' words that don't generalise past the sample: "
          f"{s['recurring_words_fail_to_generalise']}/{s['recurring_words_total']}")
    print(f"  posts the voice profile was actually extracted from:   "
          f"{s['posts_shown_to_extractor_total']} of {s['pillar_posts_total']} clustered")
    print(f"  smallest content pillar:                               "
          f"{s['smallest_pillar_post_count']} posts")


if __name__ == "__main__":
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    report = audit(clusters, profile)
    render(report)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {REPORT_PATH.relative_to(_PROJECT_ROOT)}")
