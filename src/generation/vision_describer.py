"""
Vision preprocessor — turn a post's image (or a Reel's keyframes) into a compact
text description the text-only Granite pipeline can read.

Why a preprocessor and not a runtime call: on 8GB VRAM, granite3.1-dense:8b
(~5.5GB) and a vision model can't co-reside. So the vision model is swapped in
ONCE per post at sync time to produce `visual_description`; Granite later reasons
over that text. Vision and Granite never run concurrently → no VRAM thrash.

Model: moondream (1.7GB). qwen2.5vl:3b was tried first and gave richer output,
but at 5.4GB resident it sits at this 16GB machine's RAM edge and degraded into
`!!!!` garbage mid-batch (0/5 coherent; survived re-pull, restarts, reboot).
moondream measured 6/6 coherent at ~0.65s/call.

moondream constrains the call pattern in two measured ways:
  1. No multi-image — 3 images in one call returns a bounding box, so we send
     ONE frame per request and assemble the results here.
  2. Ignores multi-section templates — a 7-section prompt produced one line and
     stopped, so the prompts are short and direct.

Uses the local `ollama` client directly (already installed via langchain-ollama)
— its `images=[...]` multimodal API is simpler than routing base64 through
ChatOllama's message format.

Self-check (needs moondream pulled + ollama running):
    python -m src.generation.vision_describer
"""

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile

import ollama
import requests

VISION_MODEL = "moondream"
_TIMEOUT = 30

# Short and direct — moondream ignores multi-section templates.
_P_DESCRIBE = (
    "Describe this image in detail: the main subject, the setting, colors and "
    "lighting, any text visible in the image, and the overall mood."
)
_P_OCR = "What text is written in this image? Reply with the text only, or 'none'."

# Labels for the 3 keyframes of a Reel, in order.
_FRAME_LABELS = ("start", "middle", "end")


def _download(url: str) -> bytes:
    resp = requests.get(url, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.content


def _encode_jpeg(frame) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(frame).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _downscale_b64(jpg: bytes, maxside: int = 512) -> str:
    """Shrink to <=maxside long-edge, normalise to JPEG, return base64.

    qwen2.5-VL expands each image into ~(w/28)*(h/28) vision tokens; three
    720x1280 frames alone would exceed the 4096 context and produce garbage.
    Downscaling keeps 3 frames well within context and speeds inference.
    """
    from PIL import Image
    im = Image.open(io.BytesIO(jpg)).convert("RGB")
    im.thumbnail((maxside, maxside))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _keyframes_from_video_bytes(data: bytes) -> list[bytes]:
    """Extract 3 keyframes (start / middle / end) as JPEG bytes. [] on any failure."""
    # ponytail: fixed start/mid/end sampling. Upgrade to scene-change detection
    # only if Reels need it.
    import imageio  # bundled ffmpeg binary via imageio-ffmpeg — no system install

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tf.write(data)
            path = tf.name  # closed here so Windows lets imageio open it

        reader = imageio.get_reader(path)
        # count_frames() is accurate for well-formed mp4 (IG reels). The
        # duration*fps estimate overshoots the real count, so the end index
        # runs past EOF → IndexError. Trust the count; estimate only as fallback.
        try:
            n = int(reader.count_frames())
        except Exception:
            n = 0
        if n <= 0:
            try:
                meta = reader.get_meta_data()
                dur, fps = meta.get("duration"), meta.get("fps")
                n = int(dur * fps) if (dur and fps) else 0
            except Exception:
                n = 0

        if n <= 0:  # unknown length → decode sequentially (short/odd clips only)
            frames = list(reader)
            reader.close()
            if not frames:
                return []
            m = len(frames)
            return [_encode_jpeg(frames[i]) for i in (0, m // 2, m - 1)]

        # Tolerate a fuzzy EOF: keep the frames that decode, stepping the index
        # back a little rather than abandoning all three on one bad index.
        arrs = []
        for i in (0, n // 2, n - 1):
            for j in (i, i - 1, i - 2):
                if j < 0:
                    break
                try:
                    arrs.append(reader.get_data(j))
                    break
                except Exception:
                    continue
        reader.close()
        return [_encode_jpeg(a) for a in arrs] if arrs else []
    except Exception as exc:
        print(f"  keyframe extraction failed: {exc}", file=sys.stderr)
        return []
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass


class VisionDescriber:
    def __init__(self, model: str = VISION_MODEL):
        self.model = model

    def _ask(self, prompt: str, image_b64: str, num_predict: int) -> str:
        """One single-image question. Returns '' if the model emits NaN garbage."""
        resp = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt, "images": [image_b64]}],
            options={"temperature": 0, "num_predict": num_predict},
        )
        out = (resp.get("message", {}).get("content") or "").strip()
        # A wedged vision runner emits runs of "!" instead of text. A short "!!!"
        # prefix on otherwise-good output is a known harmless artifact, so strip
        # leading punctuation first and only reject what is *mostly* "!".
        out = out.lstrip("!").strip()
        if not out or out.count("!") > len(out) / 2:
            return ""
        return out

    def _run(self, images: list[bytes], multi_frame: bool) -> str:
        """One request per frame (moondream is single-image), assembled here."""
        blocks = []
        for i, im in enumerate(images):
            b64 = _downscale_b64(im)
            desc = self._ask(_P_DESCRIBE, b64, num_predict=300)
            if not desc:
                continue
            text = self._ask(_P_OCR, b64, num_predict=100) or "none"
            if multi_frame:
                label = _FRAME_LABELS[i] if i < len(_FRAME_LABELS) else str(i + 1)
                blocks.append(f"FRAME {i + 1} ({label}): {desc}\nON-IMAGE TEXT: {text}")
            else:
                blocks.append(f"{desc}\nON-IMAGE TEXT: {text}")
        return "\n\n".join(blocks)

    def describe(self, record: dict) -> str:
        """Describe a canonical scraped_dataset record. '' if no usable media."""
        content    = record.get("content", {})
        media_type = (content.get("media_type") or "").upper()
        media_url  = content.get("media_url") or ""
        thumb_url  = content.get("thumbnail_url") or ""
        is_reel    = media_type == "VIDEO"

        if is_reel and media_url:
            try:
                frames = _keyframes_from_video_bytes(_download(media_url))
            except Exception:
                frames = []
            if not frames and thumb_url:  # fall back to the cover frame
                frames = [_download(thumb_url)]
            images = frames
        else:
            src = media_url or thumb_url
            images = [_download(src)] if src else []

        if not images:
            return ""
        return self._run(images, multi_frame=len(images) > 1)

    def describe_bytes(self, data: bytes, is_video: bool) -> str:
        """Describe a raw uploaded image or video (manual Why Engine form)."""
        if is_video:
            images = _keyframes_from_video_bytes(data)
        else:
            images = [data]
        if not images:
            return ""
        return self._run(images, multi_frame=len(images) > 1)


def is_usable_description(desc: str) -> bool:
    """
    True if a stored visual_description is real text rather than model garbage.

    A wedged vision runner emits runs of "!" (see `_ask`). Older batches ran
    before that guard existed and persisted such junk, so treat it as missing
    and let the backfill regenerate it.
    """
    d = (desc or "").strip()
    return bool(d) and d.count("!") <= len(d) / 2


def backfill_descriptions(scraped_dir, force: bool = False) -> int:
    """
    Fill `content.visual_description` for every post lacking a usable one.

    Must run right after sync — Graph API media_url/thumbnail_url are short-lived
    CDN links. Idempotent: skips posts already described. Never raises per-post;
    visual_description is additive and must not block the text pipeline.
    """
    import json
    from pathlib import Path

    scraped_dir = Path(scraped_dir)
    describer = VisionDescriber()
    count = 0
    for f in sorted(scraped_dir.glob("ig_text_*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        content = rec.get("content", {})
        if is_usable_description(content.get("visual_description", "")) and not force:
            continue
        try:
            desc = describer.describe(rec)
        except Exception as exc:
            print(f"  vision skip {f.name}: {exc}", file=sys.stderr)
            continue
        if not desc:
            continue
        content["visual_description"] = desc
        rec["content"] = content
        f.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        count += 1
        print(f"  described {rec.get('shortcode', f.name)}")
    return count


def _demo() -> None:
    """Runnable check: describe a synthetic image with baked-in text."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (512, 512), (245, 220, 180))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, 452, 452], fill=(120, 70, 40))
    d.text((120, 230), "SALE 50% OFF", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    try:
        out = VisionDescriber().describe_bytes(buf.getvalue(), is_video=False)
    except Exception as exc:
        sys.exit(f"self-check needs ollama + `ollama pull {VISION_MODEL}`: {exc}")

    assert out, "expected a non-empty description"
    assert "ON-IMAGE TEXT" in out.upper(), f"missing ON-IMAGE TEXT section:\n{out}"
    assert "FRAME" not in out.upper(), f"single image must not be frame-labelled:\n{out}"

    # Multi-frame assembly (the Reel path) — same image twice stands in for
    # keyframes, so this checks the labelling without encoding a video.
    multi = VisionDescriber()._run([buf.getvalue()] * 2, multi_frame=True)
    assert "FRAME 1 (start)" in multi and "FRAME 2 (middle)" in multi, \
        f"multi-frame labels missing:\n{multi}"

    print("OK — vision self-check passed:\n")
    print(out)


if __name__ == "__main__":
    _demo()
