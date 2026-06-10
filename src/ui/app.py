"""
StyleSync — AI Art Direction Assistant
Streamlit UI

Run:
    streamlit run src/ui/app.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

# Make sure project root is on sys.path when running via streamlit
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StyleSync",
    page_icon="🍩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Quiet-luxury CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Background */
  .stApp { background-color: #F9F7F4; }
  .main .block-container { padding: 2.5rem 3rem 4rem; max-width: 860px; }

  /* Typography */
  h1, h2, h3, h4 {
    font-family: Georgia, 'Times New Roman', serif;
    font-weight: 400;
    color: #1A1A1A;
    letter-spacing: -0.02em;
  }
  p, div, span, label, .stMarkdown {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #3D3D3D;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background-color: #F0EDE8;
    border-right: 1px solid #E0DAD3;
  }
  [data-testid="stSidebar"] .block-container { padding: 2rem 1.5rem; }

  /* Inputs */
  .stTextInput > div > div > input,
  .stTextArea textarea,
  .stSelectbox > div > div > div {
    background-color: #FFFFFF;
    border: 1px solid #DDD8D0;
    border-radius: 4px;
    color: #1A1A1A;
  }
  .stTextInput label, .stTextArea label, .stSelectbox label {
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7A6F63;
  }

  /* Primary button */
  .stButton > button {
    background-color: #2D2D2D;
    color: #F9F7F4;
    border: none;
    border-radius: 4px;
    padding: 0.6rem 2.2rem;
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    transition: background 0.15s;
  }
  .stButton > button:hover { background-color: #8B7355; }

  /* Divider */
  hr { border: none; border-top: 1px solid #E0DAD3; margin: 1.8rem 0; }

  /* Tone pill tags */
  .tone-tag {
    display: inline-block;
    background: #F9F7F4;
    border: 1px solid #D5CEC6;
    border-radius: 20px;
    padding: 0.18rem 0.8rem;
    font-size: 0.72rem;
    color: #5A4F44;
    margin: 0.15rem 0.1rem;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    letter-spacing: 0.03em;
  }

  /* Caption cards */
  .caption-card {
    background: #FFFFFF;
    border: 1px solid #E8E3DC;
    border-radius: 6px;
    padding: 1.4rem 1.6rem 1.2rem;
    margin-bottom: 1rem;
  }
  .caption-variant-label {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9A8F83;
    margin-bottom: 0.6rem;
  }
  .caption-reasoning {
    font-size: 0.78rem;
    color: #8B7355;
    font-style: italic;
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #F0EDE8;
  }

  /* Image prompt card */
  .image-prompt-card {
    background: #242220;
    border-radius: 6px;
    padding: 1.6rem;
    margin-top: 0.5rem;
  }
  .image-prompt-text {
    font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 0.85rem;
    line-height: 1.65;
    color: #E8E3DC;
  }
  .image-prompt-note {
    font-size: 0.75rem;
    color: #7A8FA0;
    font-style: italic;
    margin-top: 0.75rem;
  }

  /* Section label */
  .section-label {
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #9A8F83;
    margin-bottom: 0.3rem;
  }

  /* Spinner */
  .stSpinner { color: #8B7355 !important; }
</style>
""", unsafe_allow_html=True)


# ── Data & model loading ──────────────────────────────────────────────────────

@st.cache_data
def load_profile() -> dict:
    if not BRAND_PROFILE_PATH.exists():
        st.error(
            "Brand profile not found. Run `python run_pipeline.py` first "
            "to generate `data/brand_profile.json`."
        )
        st.stop()
    return json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))


@st.cache_resource
def get_caption_generator():
    from src.generation.caption_generator import CaptionGenerator
    return CaptionGenerator()


@st.cache_resource
def get_image_generator():
    from src.generation.image_prompt_generator import ImagePromptGenerator
    return ImagePromptGenerator()


# ── Sidebar: Brand DNA ────────────────────────────────────────────────────────

def render_sidebar(profile: dict):
    with st.sidebar:
        st.markdown("### HotCakes Bakes")
        st.markdown(
            f"<div style='font-size:0.82rem; color:#7A6F63; margin-bottom:0.3rem;'>"
            f"{profile['ig_handle']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.82rem; line-height:1.55; color:#5A4F44;'>"
            f"{profile['brand_bio']}</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            "<div class='section-label'>Brand DNA — 5 Content Pillars</div>",
            unsafe_allow_html=True,
        )

        pillar_labels = {
            "product_showcase": "Product Showcase",
            "behind_scenes"   : "Behind the Scenes",
            "seasonal_special": "Seasonal Special",
            "customer_connection": "Customer Connection",
            "brand_story"     : "Brand Story",
        }

        for cp in profile["cluster_profiles"]:
            p = cp.get("profile", {})
            if p.get("parse_error"):
                continue
            raw_pillar = p.get("content_pillar", "product_showcase")
            pillar     = pillar_labels.get(raw_pillar, raw_pillar.replace("_", " ").title())
            tones      = p.get("tone_descriptors", [])
            phrases    = p.get("vocabulary_patterns", {}).get("signature_phrases", [])

            with st.expander(f"C{cp['cluster_id']} · {pillar}  ({cp['post_count']} posts)"):
                tags = "".join(f"<span class='tone-tag'>{t}</span>" for t in tones)
                st.markdown(tags, unsafe_allow_html=True)
                if phrases:
                    st.markdown("<br>", unsafe_allow_html=True)
                    for phrase in phrases[:2]:
                        st.markdown(
                            f"<div style='font-size:0.8rem; color:#5A4F44; "
                            f"font-style:italic; margin:0.2rem 0;'>"{phrase}"</div>",
                            unsafe_allow_html=True,
                        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    profile = load_profile()
    render_sidebar(profile)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## StyleSync")
    st.markdown(
        "<div style='color:#7A6F63; font-size:0.9rem; margin-top:-0.4rem;'>"
        "AI Art Direction for HotCakes Bakes — on-brand captions and image prompts</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Build cluster selector options ────────────────────────────────────────
    cluster_options: dict[str, int] = {}
    pillar_labels = {
        "product_showcase"   : "Product Showcase",
        "behind_scenes"      : "Behind the Scenes",
        "seasonal_special"   : "Seasonal Special",
        "customer_connection": "Customer Connection",
        "brand_story"        : "Brand Story",
    }
    for cp in profile["cluster_profiles"]:
        p = cp.get("profile", {})
        if p.get("parse_error"):
            continue
        raw_pillar = p.get("content_pillar", "product_showcase")
        pillar     = pillar_labels.get(raw_pillar, raw_pillar.replace("_", " ").title())
        tones      = p.get("tone_descriptors", [])
        tone_str   = " · ".join(tones[:2]) if tones else ""
        label      = f"C{cp['cluster_id']} — {pillar}  [{tone_str}]"
        cluster_options[label] = cp["cluster_id"]

    # ── Brief form ────────────────────────────────────────────────────────────
    st.markdown("### Content Brief")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        product = st.text_input(
            "Product",
            placeholder="Nutella Bomboloni, Rasmalai Cake, Brownie Box…",
            help="The specific product you're creating content for",
        )
        occasion = st.text_input(
            "Occasion",
            placeholder="Weekend drop, Valentine's Day, Bulk order promo…",
            help="What is this post for?",
        )

    with col_right:
        desired_feel = st.text_area(
            "Desired Feel",
            placeholder=(
                "Indulgent and enticing — focus on the Nutella filling "
                "and the craving trigger. Keep it short and punchy."
            ),
            height=108,
            help="The mood, angle, or specific detail you want to highlight",
        )
        selected_voice = st.selectbox(
            "Brand Voice Cluster",
            options=list(cluster_options.keys()),
            help="Choose the content pillar that best fits this post",
        )

    cluster_id = cluster_options[selected_voice]

    st.markdown("<br>", unsafe_allow_html=True)
    generate = st.button("Generate Captions")

    # ── Results ───────────────────────────────────────────────────────────────
    if generate:
        if not product.strip():
            st.warning("Please enter a product name.")
            return
        if not occasion.strip():
            st.warning("Please enter an occasion.")
            return

        st.divider()
        st.markdown("### Caption Variants")

        # ── Caption generation ────────────────────────────────────────────────
        with st.spinner("Writing captions…"):
            try:
                cap_gen  = get_caption_generator()
                captions = cap_gen.generate(
                    product     = product.strip(),
                    occasion    = occasion.strip(),
                    desired_feel= desired_feel.strip() or "on-brand and engaging",
                    cluster_id  = cluster_id,
                )
            except Exception as exc:
                st.error(f"Caption generation failed: {exc}")
                st.info("Make sure Ollama is running: `ollama serve`")
                return

        if not captions:
            st.error("No captions returned — try rephrasing the brief.")
            return

        first_caption = captions[0].get("caption", "") if captions else ""

        for i, item in enumerate(captions, 1):
            caption_text = item.get("caption", "").strip()
            reasoning    = item.get("reasoning", "").strip()

            if not caption_text:
                continue

            st.markdown(
                f"<div class='caption-card'>"
                f"<div class='caption-variant-label'>Variant {i}</div>",
                unsafe_allow_html=True,
            )
            # Use st.code for easy copy + no HTML injection risk
            st.code(caption_text, language=None)
            if reasoning:
                st.markdown(
                    f"<div class='caption-reasoning'>↳ {reasoning}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Image prompt ──────────────────────────────────────────────────────
        if first_caption:
            st.divider()
            st.markdown("### Image Direction Prompt")
            st.markdown(
                "<div style='font-size:0.82rem; color:#7A6F63; margin-bottom:1rem;'>"
                "Based on Variant 1 — paste into Midjourney, DALL-E 3, or Stable Diffusion."
                "</div>",
                unsafe_allow_html=True,
            )

            with st.spinner("Generating visual direction…"):
                try:
                    img_gen    = get_image_generator()
                    img_result = img_gen.generate(
                        caption = first_caption,
                        product = product.strip(),
                    )
                except Exception as exc:
                    st.error(f"Image prompt generation failed: {exc}")
                    return

            prompt_text = img_result.get("prompt", "").strip()
            style_notes = img_result.get("style_notes", "").strip()

            if prompt_text:
                st.markdown(
                    f"<div class='image-prompt-card'>"
                    f"<div class='image-prompt-text'>{prompt_text}</div>"
                    + (
                        f"<div class='image-prompt-note'>↳ {style_notes}</div>"
                        if style_notes else ""
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
                # Copyable version
                st.code(prompt_text, language=None)


if __name__ == "__main__":
    main()
