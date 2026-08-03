"""
Regenerate the StyleSync arm with measured structural constraints.

Reads the briefs and baseline captions already produced by eval/generate.py and
reuses them verbatim, regenerating only the StyleSync caption — this time with
per-pillar word-count and hashtag targets measured from the train split.

Holding the brief and the baseline fixed is the point: the only variable between
captions.json and captions_constrained.json is whether generation was told the
account's real caption shape. Anything the scores do is attributable to that.

Style stats come from clusters_train.json, never from the held-out posts.

40 Granite calls. Cached per shortcode, so an interrupted run resumes.

Run (after eval/generate.py):
    python eval/generate_constrained.py
"""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.style_stats import compute_pillar_style  # noqa: E402
from src.generation.caption_generator import CaptionGenerator  # noqa: E402

ARTIFACTS = _PROJECT_ROOT / "eval" / "artifacts"
SOURCE_PATH = ARTIFACTS / "captions.json"
TRAIN_CLUSTERS_PATH = ARTIFACTS / "clusters_train.json"
HOLDOUT_PROFILE_PATH = ARTIFACTS / "profile_holdout.json"
OUT_PATH = ARTIFACTS / "captions_constrained.json"

DESIRED_FEEL = "natural"


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    train_clusters = json.loads(TRAIN_CLUSTERS_PATH.read_text(encoding="utf-8"))

    style_by_cluster = {
        cid: compute_pillar_style(train_clusters, cid)
        for cid in range(train_clusters["n_clusters"])
    }
    print("── Measured style targets (from TRAIN posts only)")
    for cid, st in style_by_cluster.items():
        print(f"   pillar {cid}: {st['words']} words, {st['hashtags']} hashtags, "
              f"{st['emoji']} emoji  [{st['scope']}, n={st['n_posts']}]")

    generator = CaptionGenerator(profile_path=HOLDOUT_PROFILE_PATH)

    out = json.loads(OUT_PATH.read_text(encoding="utf-8")) if OUT_PATH.exists() else {}
    print(f"\n── {len(source)} items · {len(out)} already cached\n")

    for i, (sc, item) in enumerate(source.items(), 1):
        if sc in out:
            print(f"  [{i:>2}/{len(source)}] {sc}  cached")
            continue

        cid = item["assigned_cluster"]
        variants = generator.generate(
            product=item["brief"]["product"],
            occasion=item["brief"]["occasion"],
            desired_feel=DESIRED_FEEL,
            cluster_id=cid,
            style_constraints=style_by_cluster.get(cid),
        )
        caption = (variants[0].get("caption", "") if variants else "").strip()

        out[sc] = {**item, "stylesync": caption}
        OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"  [{i:>2}/{len(source)}] {sc}  c{cid}  "
              f"{len(caption.split()):>3}w {caption.count('#')}#  "
              f"(was {len(item['stylesync'].split()):>3}w {item['stylesync'].count('#')}#)")

    before_w = sum(len(v["stylesync"].split()) for v in source.values()) / len(source)
    after_w = sum(len(v["stylesync"].split()) for v in out.values()) / len(out)
    before_h = sum(v["stylesync"].count("#") for v in source.values()) / len(source)
    after_h = sum(v["stylesync"].count("#") for v in out.values()) / len(out)

    print(f"\n── StyleSync arm: {before_w:.1f} → {after_w:.1f} words, "
          f"{before_h:.1f} → {after_h:.1f} hashtags")
    print(f"Saved → {OUT_PATH.relative_to(_PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
