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
  .stApp { background-color: #F9F7F4; }
  .main .block-container { padding: 2.5rem 3rem 4rem; max-width: 860px; }

  h1, h2, h3, h4 {
    font-family: Georgia, 'Times New Roman', serif;
    font-weight: 400; color: #1A1A1A; letter-spacing: -0.02em;
  }
  p, div, span, label, .stMarkdown {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #3D3D3D;
  }

  [data-testid="stSidebar"] {
    background-color: #F0EDE8; border-right: 1px solid #E0DAD3;
  }
  [data-testid="stSidebar"] .block-container { padding: 2rem 1.5rem; }

  .stTextInput > div > div > input,
  .stTextArea textarea,
  .stSelectbox > div > div > div,
  .stNumberInput > div > div > input {
    background-color: #FFFFFF; border: 1px solid #DDD8D0;
    border-radius: 4px; color: #1A1A1A;
  }
  .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label {
    font-size: 0.78rem; letter-spacing: 0.06em;
    text-transform: uppercase; color: #7A6F63;
  }

  .stButton > button {
    background-color: #2D2D2D; color: #F9F7F4; border: none;
    border-radius: 4px; padding: 0.6rem 2.2rem;
    font-size: 0.82rem; letter-spacing: 0.08em; text-transform: uppercase;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  .stButton > button:hover { background-color: #8B7355; }

  hr { border: none; border-top: 1px solid #E0DAD3; margin: 1.8rem 0; }

  .tone-tag {
    display: inline-block; background: #F9F7F4;
    border: 1px solid #D5CEC6; border-radius: 20px;
    padding: 0.18rem 0.8rem; font-size: 0.72rem; color: #5A4F44;
    margin: 0.15rem 0.1rem; letter-spacing: 0.03em;
  }

  /* Caption cards */
  .caption-variant-label {
    font-size: 0.7rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: #9A8F83; margin-bottom: 0.6rem;
  }
  .caption-reasoning {
    font-size: 0.78rem; color: #8B7355; font-style: italic;
    margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #F0EDE8;
  }

  /* Image prompt card */
  .image-prompt-card {
    background: #242220; border-radius: 6px; padding: 1.6rem; margin-top: 0.5rem;
  }
  .image-prompt-text {
    font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 0.85rem; line-height: 1.65; color: #E8E3DC;
  }
  .image-prompt-note { font-size: 0.75rem; color: #7A8FA0; font-style: italic; margin-top: 0.75rem; }

  /* Why Engine verdict cards */
  .verdict-succeeded   { border-left: 3px solid #5A8A6A; }
  .verdict-underperformed { border-left: 3px solid #C4A35A; }
  .verdict-failed      { border-left: 3px solid #A35A5A; }

  .diagnosis-card {
    background: #FFFFFF; border: 1px solid #E8E3DC; border-radius: 6px;
    padding: 1.4rem 1.6rem; margin-bottom: 0.8rem;
  }
  .diagnosis-label {
    font-size: 0.7rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: #9A8F83; margin-bottom: 0.5rem;
  }
  .gap-card {
    background: #FDF8F2; border: 1px solid #E8DFD0; border-radius: 6px;
    padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
  }
  .section-label {
    font-size: 0.7rem; letter-spacing: 0.12em;
    text-transform: uppercase; color: #9A8F83; margin-bottom: 0.3rem;
  }

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] { gap: 2rem; border-bottom: 1px solid #E0DAD3; }
  .stTabs [data-baseweb="tab"] {
    font-size: 0.82rem; letter-spacing: 0.06em; text-transform: uppercase;
    color: #7A6F63; padding: 0.5rem 0; background: transparent; border: none;
  }
  .stTabs [aria-selected="true"] { color: #1A1A1A; border-bottom: 2px solid #2D2D2D; }
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


@st.cache_resource
def get_why_engine():
    from src.generation.why_engine import WhyEngine
    return WhyEngine()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_cluster_options(profile: dict) -> dict[str, int]:
    pillar_labels = {
        "product_showcase"   : "Product Showcase",
        "behind_scenes"      : "Behind the Scenes",
        "seasonal_special"   : "Seasonal Special",
        "customer_connection": "Customer Connection",
        "brand_story"        : "Brand Story",
    }
    options: dict[str, int] = {}
    for cp in profile["cluster_profiles"]:
        p = cp.get("profile", {})
        if p.get("parse_error"):
            continue
        raw_pillar = p.get("content_pillar", "product_showcase")
        pillar     = pillar_labels.get(raw_pillar, raw_pillar.replace("_", " ").title())
        tones      = p.get("tone_descriptors", [])
        tone_str   = " · ".join(tones[:2]) if tones else ""
        label      = f"C{cp['cluster_id']} — {pillar}  [{tone_str}]"
        options[label] = cp["cluster_id"]
    return options


# ── Sidebar: Brand DNA ────────────────────────────────────────────────────────

def render_sidebar(profile: dict):
    pillar_labels = {
        "product_showcase"   : "Product Showcase",
        "behind_scenes"      : "Behind the Scenes",
        "seasonal_special"   : "Seasonal Special",
        "customer_connection": "Customer Connection",
        "brand_story"        : "Brand Story",
    }
    with st.sidebar:
        st.markdown("### HotCakes Bakes")
        st.markdown(
            f"<div style='font-size:0.82rem;color:#7A6F63;margin-bottom:0.3rem;'>"
            f"{profile['ig_handle']}</div>", unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.82rem;line-height:1.55;color:#5A4F44;'>"
            f"{profile['brand_bio']}</div>", unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            "<div class='section-label'>Brand DNA — 5 Content Pillars</div>",
            unsafe_allow_html=True,
        )
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
                            f"<div style='font-size:0.8rem;color:#5A4F44;"
                            f"font-style:italic;margin:0.2rem 0;'>&Idquo;{phrase}&Idquo;</div>",
                            unsafe_allow_html=True,
                        )


# ── Tab 1: Caption Generator ──────────────────────────────────────────────────

def render_caption_tab(profile: dict):
    cluster_options = _build_cluster_options(profile)

    st.markdown("### Content Brief")
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        product = st.text_input(
            "Product",
            placeholder="Nutella Bomboloni, Rasmalai Cake, Brownie Box…",
        )
        occasion = st.text_input(
            "Occasion",
            placeholder="Weekend drop, Valentine's Day, Bulk order promo…",
        )

    with col_right:
        desired_feel = st.text_area(
            "Desired Feel",
            placeholder="Indulgent and enticing — focus on the Nutella filling.",
            height=108,
        )
        selected_voice = st.selectbox(
            "Brand Voice Cluster",
            options=list(cluster_options.keys()),
        )

    cluster_id = cluster_options[selected_voice]
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Generate Captions"):
        if not product.strip():
            st.warning("Please enter a product name.")
            return
        if not occasion.strip():
            st.warning("Please enter an occasion.")
            return

        st.divider()
        st.markdown("### Caption Variants")

        with st.spinner("Writing captions…"):
            try:
                captions = get_caption_generator().generate(
                    product      = product.strip(),
                    occasion     = occasion.strip(),
                    desired_feel = desired_feel.strip() or "on-brand and engaging",
                    cluster_id   = cluster_id,
                )
            except Exception as exc:
                st.error(f"Caption generation failed: {exc}")
                st.info("Make sure Ollama is running: `ollama serve`")
                return

        if not captions:
            st.error("No captions returned — try rephrasing your brief.")
            return

        first_caption = captions[0].get("caption", "") if captions else ""

        for i, item in enumerate(captions, 1):
            caption_text = item.get("caption", "").strip()
            reasoning    = item.get("reasoning", "").strip()
            if not caption_text:
                continue
            st.markdown(
                f"<div class='caption-variant-label'>Variant {i}</div>",
                unsafe_allow_html=True,
            )
            st.code(caption_text, language=None)
            if reasoning:
                st.markdown(
                    f"<div class='caption-reasoning'>↳ {reasoning}</div>",
                    unsafe_allow_html=True,
                )

        if first_caption:
            st.divider()
            st.markdown("### Image Direction Prompt")
            st.markdown(
                "<div style='font-size:0.82rem;color:#7A6F63;margin-bottom:1rem;'>"
                "Based on Variant 1 — paste into Midjourney, DALL-E 3, or Stable Diffusion.</div>",
                unsafe_allow_html=True,
            )
            with st.spinner("Generating visual direction…"):
                try:
                    img_result = get_image_generator().generate(
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
                    + (f"<div class='image-prompt-note'>↳ {style_notes}</div>" if style_notes else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.code(prompt_text, language=None)


# ── Tab 2: Post Mortem (Why Engine) ──────────────────────────────────────────

def render_postmortem_tab(profile: dict):
    cluster_options = _build_cluster_options(profile)

    st.markdown("### Post Mortem — Why Engine")
    st.markdown(
        "<div style='font-size:0.88rem;color:#7A6F63;margin-bottom:1.5rem;'>"
        "Paste a post's caption and its Instagram Insights. Granite cross-references "
        "the metrics against your brand's established content patterns and diagnoses "
        "exactly why it succeeded or failed — in plain English.</div>",
        unsafe_allow_html=True,
    )

    # ── Caption & post metadata ───────────────────────────────────────────────
    col_a, col_b = st.columns([2, 1], gap="large")

    with col_a:
        pm_caption = st.text_area(
            "Caption you posted",
            placeholder=(
                'e.g. "Chocolate Cake 🤎\n\nTo order / enquire DM @hot_cakesbakes"'
            ),
            height=130,
        )
    with col_b:
        pm_post_type = st.selectbox(
            "Post type",
            ["Reel", "Carousel", "Static Photo"],
            key="pm_post_type",
        )
        pm_cluster = st.selectbox(
            "Content cluster",
            options=list(cluster_options.keys()),
            key="pm_cluster",
            help="Choose the cluster that best describes this post",
        )

    col_day, col_hour = st.columns(2, gap="large")
    with col_day:
        pm_day = st.selectbox(
            "Day posted",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=4,
            key="pm_day",
        )
    with col_hour:
        pm_hour = st.selectbox(
            "Time posted",
            [
                "6:00 AM", "7:00 AM", "8:00 AM", "9:00 AM", "10:00 AM",
                "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM",
                "4:00 PM", "5:00 PM", "6:00 PM", "7:00 PM", "8:00 PM",
                "9:00 PM", "10:00 PM", "11:00 PM",
            ],
            index=12,
            key="pm_hour",
        )

    # ── Metrics input ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-label'>Instagram Insights</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.78rem;color:#9A8F83;margin-bottom:1rem;'>"
        "Find these in Instagram → Professional Dashboard → Content → tap the post.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        pm_views    = st.number_input("Views",     min_value=0, value=420, step=10, key="pm_views")
        pm_likes    = st.number_input("Likes",     min_value=0, value=22,  step=1,  key="pm_likes")
    with c2:
        pm_shares   = st.number_input("Shares",    min_value=0, value=1,   step=1,  key="pm_shares")
        pm_comments = st.number_input("Comments",  min_value=0, value=2,   step=1,  key="pm_comments")
    with c3:
        pm_saves    = st.number_input("Saves",     min_value=0, value=3,   step=1,  key="pm_saves")
        pm_hook     = st.number_input(
            "Hook rate %",
            min_value=0.0, max_value=100.0, value=18.0, step=0.5,
            help="% who watched past the first 3 seconds",
            key="pm_hook",
        )
    with c4:
        pm_watch    = st.number_input(
            "Watch time %",
            min_value=0.0, max_value=100.0, value=28.0, step=0.5,
            help="Average % of the video watched",
            key="pm_watch",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Run Post Mortem", key="pm_btn"):
        if not pm_caption.strip():
            st.warning("Please paste the caption you posted.")
            return

        st.divider()

        with st.spinner("Diagnosing post with Granite…"):
            try:
                result = get_why_engine().analyze(
                    caption        = pm_caption.strip(),
                    post_type      = pm_post_type,
                    posted_day     = pm_day,
                    posted_hour    = pm_hour,
                    views          = int(pm_views),
                    watch_time_pct = float(pm_watch),
                    hook_rate      = float(pm_hook),
                    shares         = int(pm_shares),
                    saves          = int(pm_saves),
                    likes          = int(pm_likes),
                    comments       = int(pm_comments),
                    cluster_id     = cluster_options[pm_cluster],
                )
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.info("Make sure Ollama is running: `ollama serve`")
                return

        verdict_class = {
            "succeeded"     : "verdict-succeeded",
            "underperformed": "verdict-underperformed",
            "failed"        : "verdict-failed",
        }.get(result.get("verdict", "underperformed"), "verdict-underperformed")

        # ── Verdict banner ────────────────────────────────────────────────────
        verdict_colors = {
            "succeeded"     : "#5A8A6A",
            "underperformed": "#C4A35A",
            "failed"        : "#A35A5A",
        }
        verdict_key = result.get("verdict", "underperformed")
        verdict_color = verdict_colors.get(verdict_key, "#C4A35A")

        st.markdown(
            f"<div style='font-size:1.1rem;font-family:Georgia,serif;"
            f"color:{verdict_color};margin-bottom:1.5rem;letter-spacing:-0.01em;'>"
            f"{result.get('verdict_label', '—')}</div>",
            unsafe_allow_html=True,
        )

        # ── Diagnosis ─────────────────────────────────────────────────────────
        def _block(label: str, content: str, css_class: str = "diagnosis-card"):
            st.markdown(
                f"<div class='{css_class} {verdict_class}'>"
                f"<div class='diagnosis-label'>{label}</div>"
                f"<div style='font-size:0.9rem;line-height:1.6;'>{content}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        _block("Overall Diagnosis", result.get("diagnosis", ""))

        col_good, col_bad = st.columns(2, gap="medium")
        with col_good:
            _block("What Worked", result.get("what_worked", "N/A"))
        with col_bad:
            _block("What Failed", result.get("what_failed", "—"))

        # Brand voice gap — highlighted differently
        st.markdown(
            f"<div class='gap-card'>"
            f"<div class='diagnosis-label'>Brand Voice Gap</div>"
            f"<div style='font-size:0.88rem;line-height:1.6;color:#5A4F44;font-style:italic;'>"
            f"{result.get('brand_voice_gap', '—')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Change next time — actionable
        st.markdown("#### Change Next Time")
        change_text = result.get("change_next_time", "")
        for line in change_text.split("\n"):
            line = line.strip().lstrip("•-123456789. ")
            if line:
                st.markdown(f"→ {line}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    profile = load_profile()
    render_sidebar(profile)

    st.markdown("## StyleSync")
    st.markdown(
        "<div style='color:#7A6F63;font-size:0.9rem;margin-top:-0.4rem;'>"
        "AI Art Direction for HotCakes Bakes</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    tab_captions, tab_postmortem = st.tabs(["Generate Captions", "Post Mortem"])

    with tab_captions:
        render_caption_tab(profile)

    with tab_postmortem:
        render_postmortem_tab(profile)


if __name__ == "__main__":
    main()


