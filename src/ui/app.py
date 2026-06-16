"""
StyleSync — Creative Intelligence Platform
Streamlit UI

Run:
    streamlit run src/ui/app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make sure project root is on sys.path when running via streamlit
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"
CLUSTERS_PATH      = _PROJECT_ROOT / "data" / "clusters.json"

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
  .verdict-succeeded      { border-left: 3px solid #5A8A6A; }
  .verdict-underperformed { border-left: 3px solid #C4A35A; }
  .verdict-failed         { border-left: 3px solid #A35A5A; }

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

  /* Solver cards */
  .solver-direction-card {
    background: #FFFFFF; border: 1px solid #E8E3DC; border-radius: 6px;
    padding: 1rem 1.2rem; margin-bottom: 0.6rem;
  }
  .solver-applied-banner {
    background: #EFF5F0; border: 1px solid #C5D9C8; border-radius: 4px;
    padding: 0.7rem 1rem; font-size: 0.82rem; color: #3D6B47;
    margin-bottom: 1rem;
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


# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data
def load_profile() -> dict:
    if not BRAND_PROFILE_PATH.exists():
        st.error(
            "Brand profile not found. Run `python run_pipeline.py` first "
            "to generate `data/brand_profile.json`."
        )
        st.stop()
    return json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_clusters() -> dict:
    if not CLUSTERS_PATH.exists():
        st.error(
            "Clusters data not found. Run `python run_pipeline.py` first "
            "to generate `data/clusters.json`."
        )
        st.stop()
    return json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))


# ── Model / generator loaders ─────────────────────────────────────────────────

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


@st.cache_resource
def get_moment_analyzer():
    from src.generation.blank_page_solver import MomentAnalyzer
    return MomentAnalyzer()


@st.cache_resource
def get_direction_generator():
    from src.generation.blank_page_solver import DirectionGenerator
    return DirectionGenerator()


@st.cache_resource
def get_voice_timeline():
    from src.generation.voice_timeline import VoiceTimeline
    return VoiceTimeline()


@st.cache_resource
def get_strategic_insights():
    from src.generation.strategic_insights import StrategicInsights
    return StrategicInsights()


# ── Cached heavy computations for the Discover tab ────────────────────────────

@st.cache_data
def _compute_monthly_distribution(clusters_json: str):
    clusters = json.loads(clusters_json)
    return get_voice_timeline().compute_monthly_distribution(clusters)


@st.cache_data
def _get_timeline_narrative(monthly_counts_json: str, profile_json: str) -> dict:
    counts  = json.loads(monthly_counts_json)
    profile = json.loads(profile_json)
    return get_voice_timeline().narrate_evolution(counts, profile)


@st.cache_data
def _compute_richness_scores(profile_json: str, clusters_json: str) -> list:
    profile  = json.loads(profile_json)
    clusters = json.loads(clusters_json)
    return get_strategic_insights().compute_richness_scores(profile, clusters)


@st.cache_data
def _get_strategy_brief(scores_json: str, tensions_json: str, brand_name: str) -> dict:
    scores   = json.loads(scores_json)
    tensions = json.loads(tensions_json)
    profile  = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))
    return get_strategic_insights().generate_strategy_brief(scores, tensions, profile)


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
                            f"font-style:italic;margin:0.2rem 0;'>&ldquo;{phrase}&rdquo;</div>",
                            unsafe_allow_html=True,
                        )


# ── Tab 1: Create ─────────────────────────────────────────────────────────────

def render_create_tab(profile: dict):
    cluster_options = _build_cluster_options(profile)

    # ── Pre-fill from solver (must run before any widget is rendered) ─────────
    if "pending_desired_feel" in st.session_state:
        st.session_state["desired_feel_input"] = st.session_state.pop("pending_desired_feel")
    if "pending_cluster_label" in st.session_state:
        pending_label = st.session_state.pop("pending_cluster_label")
        if pending_label in cluster_options:
            st.session_state["cluster_voice_input"] = pending_label

    # ── Blank Page Solver ─────────────────────────────────────────────────────
    with st.expander("✦  Start from a real moment  (optional)", expanded=False):
        st.markdown(
            "<div style='font-size:0.85rem;color:#7A6F63;margin-bottom:1rem;'>"
            "Describe something that happened today — a delivery, a customer message, "
            "a small win, anything real. Granite will find the creative opportunity "
            "and propose 3 distinct ways to tell the story.</div>",
            unsafe_allow_html=True,
        )
        moment_text = st.text_area(
            "What happened today?",
            placeholder=(
                "e.g. I just got a DM from a cafe owner asking for a bulk weekly order "
                "— my first B2B client. I don't even know how to feel about it."
            ),
            height=100,
            key="solver_moment_text",
        )

        if st.button("Analyze My Moment", key="solver_analyze_btn"):
            if not moment_text.strip():
                st.warning("Describe a moment first.")
            else:
                try:
                    with st.spinner("Finding the creative opportunity…"):
                        analysis = get_moment_analyzer().analyze(moment_text.strip())
                        st.session_state["solver_analysis"] = analysis

                    with st.spinner("Mapping 3 creative directions…"):
                        directions = get_direction_generator().generate(
                            analysis, moment_text.strip()
                        )
                        st.session_state["solver_directions"] = directions

                except Exception as exc:
                    st.error(f"Solver failed: {exc}")
                    st.info("Make sure Ollama is running: `ollama serve`")

        # ── Show results ──────────────────────────────────────────────────────
        if "solver_analysis" in st.session_state and "solver_directions" in st.session_state:
            analysis   = st.session_state["solver_analysis"]
            directions = st.session_state["solver_directions"]

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Emotional Core", analysis.get("emotional_core", "—"))
            with col_b:
                st.metric("Business Signal", analysis.get("business_signal", "—"))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-label'>Pick a creative direction</div>",
                unsafe_allow_html=True,
            )

            for i, d in enumerate(directions):
                title = d.get("direction_title", f"Direction {i+1}")
                angle = d.get("angle", "")
                note  = d.get("tone_note", "")
                st.markdown(
                    f"<div class='solver-direction-card'>"
                    f"<div style='font-size:0.78rem;font-weight:600;color:#2D2D2D;"
                    f"letter-spacing:0.03em;margin-bottom:0.4rem;'>{i+1}. {title}</div>"
                    f"<div style='font-size:0.85rem;color:#3D3D3D;line-height:1.55;'>{angle}</div>"
                    + (f"<div style='font-size:0.78rem;color:#8B7355;font-style:italic;"
                       f"margin-top:0.4rem;'>Tone: {note}</div>" if note else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

            chosen_idx = st.radio(
                "Apply direction",
                range(len(directions)),
                format_func=lambda i: directions[i].get("direction_title", f"Direction {i+1}"),
                key="solver_chosen_idx",
                label_visibility="collapsed",
            )

            if st.button("Apply to caption form ↓", key="solver_apply_btn"):
                d = directions[chosen_idx]
                st.session_state["pending_desired_feel"] = (
                    d.get("angle", "") + " " + d.get("tone_note", "")
                ).strip()
                # Match the cluster label string from cluster_options
                target_id = analysis.get("best_cluster_id", 0)
                for label, cid in cluster_options.items():
                    if cid == target_id:
                        st.session_state["pending_cluster_label"] = label
                        break
                st.rerun()

        # Show applied-banner if solver has pre-filled the form
        if "desired_feel_input" in st.session_state and st.session_state.get("desired_feel_input"):
            if st.session_state.get("solver_directions"):
                st.markdown(
                    "<div class='solver-applied-banner'>"
                    "✓ Creative direction applied to the form below</div>",
                    unsafe_allow_html=True,
                )

    # ── Content Brief ─────────────────────────────────────────────────────────
    st.markdown("### Content Brief")
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        product = st.text_input(
            "Product",
            placeholder="Nutella Bomboloni, Rasmalai Cake, Brownie Box…",
            key="product_input",
        )
        occasion = st.text_input(
            "Occasion",
            placeholder="Weekend drop, Valentine's Day, Bulk order promo…",
            key="occasion_input",
        )

    with col_right:
        desired_feel = st.text_area(
            "Desired Feel",
            placeholder="Indulgent and enticing — focus on the Nutella filling.",
            height=108,
            key="desired_feel_input",
        )
        selected_voice = st.selectbox(
            "Brand Voice Cluster",
            options=list(cluster_options.keys()),
            key="cluster_voice_input",
        )

    cluster_id = cluster_options[selected_voice]
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Generate Captions", key="gen_captions_btn"):
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


# ── Tab 2: Analyze (Why Engine / Post Mortem) ─────────────────────────────────

def render_analyze_tab(profile: dict):
    cluster_options = _build_cluster_options(profile)

    st.markdown("### Post Mortem — Why Engine")
    st.markdown(
        "<div style='font-size:0.88rem;color:#7A6F63;margin-bottom:1.5rem;'>"
        "Paste a post's caption and its Instagram Insights. Granite cross-references "
        "the metrics against your brand's established content patterns and diagnoses "
        "exactly why it succeeded or failed — in plain English.</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([2, 1], gap="large")

    with col_a:
        pm_caption = st.text_area(
            "Caption you posted",
            placeholder='e.g. "Chocolate Cake 🤎\n\nTo order / enquire DM @hot_cakesbakes"',
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

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Instagram Insights</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.78rem;color:#9A8F83;margin-bottom:1rem;'>"
        "Instagram app → tap the post → <b>View Insights</b>. "
        "All fields are from that screen.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        pm_views    = st.number_input("Views / Plays", min_value=0, value=420, step=10,  key="pm_views")
        pm_reach    = st.number_input("Reach",         min_value=0, value=390, step=10,  key="pm_reach")
    with c2:
        pm_likes    = st.number_input("Likes",    min_value=0, value=22, step=1, key="pm_likes")
        pm_comments = st.number_input("Comments", min_value=0, value=2,  step=1, key="pm_comments")
    with c3:
        pm_shares   = st.number_input("Shares", min_value=0, value=1, step=1, key="pm_shares")
        pm_saves    = st.number_input("Saves",  min_value=0, value=3, step=1, key="pm_saves")

    pm_avg_watch = None
    if pm_post_type == "Reel":
        st.markdown("<br>", unsafe_allow_html=True)
        col_watch, col_spacer = st.columns([1, 2], gap="medium")
        with col_watch:
            raw_watch = st.number_input(
                "Avg watch time (seconds)",
                min_value=0.0, value=0.0, step=0.5,
                help='Shown as "Average watch time: Xs" on Reels Insights. Leave at 0 if not available.',
                key="pm_avg_watch",
            )
            if raw_watch > 0:
                pm_avg_watch = float(raw_watch)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Run Post Mortem", key="pm_btn"):
        if not pm_caption.strip():
            st.warning("Please paste the caption you posted.")
            return

        st.divider()

        with st.spinner("Diagnosing post with Granite…"):
            try:
                result = get_why_engine().analyze(
                    caption             = pm_caption.strip(),
                    post_type           = pm_post_type,
                    views               = int(pm_views),
                    reach               = int(pm_reach),
                    likes               = int(pm_likes),
                    comments            = int(pm_comments),
                    shares              = int(pm_shares),
                    saves               = int(pm_saves),
                    avg_watch_time_secs = pm_avg_watch,
                    cluster_id          = cluster_options[pm_cluster],
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

        verdict_colors = {
            "succeeded"     : "#5A8A6A",
            "underperformed": "#C4A35A",
            "failed"        : "#A35A5A",
        }
        verdict_key   = result.get("verdict", "underperformed")
        verdict_color = verdict_colors.get(verdict_key, "#C4A35A")

        st.markdown(
            f"<div style='font-size:1.1rem;font-family:Georgia,serif;"
            f"color:{verdict_color};margin-bottom:1.5rem;letter-spacing:-0.01em;'>"
            f"{result.get('verdict_label', '—')}</div>",
            unsafe_allow_html=True,
        )

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

        st.markdown(
            f"<div class='gap-card'>"
            f"<div class='diagnosis-label'>Brand Voice Gap</div>"
            f"<div style='font-size:0.88rem;line-height:1.6;color:#5A4F44;font-style:italic;'>"
            f"{result.get('brand_voice_gap', '—')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Change Next Time")
        change_text = result.get("change_next_time", "")
        for line in change_text.split("\n"):
            line = line.strip().lstrip("•-123456789. ")
            if line:
                st.markdown(f"→ {line}")


# ── Tab 3: Discover (Voice Timeline + Strategic Insights) ─────────────────────

def render_discover_tab(profile: dict, clusters: dict):
    # Serialise inputs for cache keys
    profile_json  = json.dumps(profile,  sort_keys=True)
    clusters_json = json.dumps(clusters, sort_keys=True)

    # ── Metrics header ────────────────────────────────────────────────────────
    total_posts = sum(cp["post_count"] for cp in profile["cluster_profiles"])
    all_months  = {
        post["timestamp_utc"][:7]
        for posts in clusters["clusters"].values()
        for post in posts
    }
    months_tracked = len(all_months)

    col1, col2, col3 = st.columns(3)
    col1.metric("Posts Analyzed",      total_posts)
    col2.metric("Months Tracked",      months_tracked)
    col3.metric("Content Territories", 5)

    st.divider()

    # ── Voice Timeline ────────────────────────────────────────────────────────
    st.markdown("### Voice Timeline")
    st.markdown(
        "<div style='font-size:0.88rem;color:#7A6F63;margin-bottom:1.2rem;'>"
        "How your creative voice has shifted month by month — which content "
        "territories you leaned into, which you pulled back from, and the "
        "moments where something changed.</div>",
        unsafe_allow_html=True,
    )

    pct_df, raw_counts = _compute_monthly_distribution(clusters_json)

    # Build readable column names for the chart legend
    pillar_labels = {
        "product_showcase"   : "Product Showcase",
        "behind_scenes"      : "Behind the Scenes",
        "seasonal_special"   : "Seasonal Special",
        "customer_connection": "Customer Connection",
        "brand_story"        : "Brand Story",
    }
    rename_map = {}
    for cp in profile["cluster_profiles"]:
        p          = cp.get("profile", {})
        raw_pillar = p.get("content_pillar", "product_showcase")
        pillar     = pillar_labels.get(raw_pillar, raw_pillar.replace("_", " ").title())
        col_key    = f"C{cp['cluster_id']}"
        if col_key in pct_df.columns:
            rename_map[col_key] = f"C{cp['cluster_id']} {pillar}"

    chart_df = pct_df.rename(columns=rename_map)
    st.area_chart(chart_df, height=280, use_container_width=True)

    st.markdown(
        "<div style='font-size:0.72rem;color:#9A8F83;margin-top:-0.5rem;margin-bottom:1.2rem;'>"
        "Stacked area — each band shows that cluster's % of monthly posts</div>",
        unsafe_allow_html=True,
    )

    # Granite narrative
    with st.spinner("Reading the creative arc…"):
        try:
            timeline_result = _get_timeline_narrative(
                json.dumps(raw_counts, sort_keys=True),
                profile_json,
            )
        except Exception as exc:
            st.error(f"Narrative generation failed: {exc}")
            st.info("Make sure Ollama is running: `ollama serve`")
            timeline_result = None

    if timeline_result:
        st.markdown(
            f"<div class='diagnosis-card'>"
            f"<div class='diagnosis-label'>Creative Arc</div>"
            f"<div style='font-size:0.9rem;line-height:1.65;'>{timeline_result.get('narrative', '')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        key_shift = timeline_result.get("key_shift", "")
        if key_shift:
            st.markdown(
                f"<div class='gap-card'>"
                f"<div class='diagnosis-label'>Key Shift</div>"
                f"<div style='font-size:0.88rem;line-height:1.6;color:#5A4F44;font-style:italic;'>"
                f"{key_shift}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Strategic Insights ────────────────────────────────────────────────────
    st.markdown("### Strategic Insights")
    st.markdown(
        "<div style='font-size:0.88rem;color:#7A6F63;margin-bottom:1.2rem;'>"
        "Where you're over-invested vs. where your richest creative voice lives. "
        "Volume % = how often you post there. Richness % = how developed that "
        "territory's vocabulary and tone is.</div>",
        unsafe_allow_html=True,
    )

    scores   = _compute_richness_scores(profile_json, clusters_json)
    tensions = get_strategic_insights().detect_tensions(scores)

    # Build rank-based bar chart (higher bar = stronger in that dimension)
    # volume_score / richness_score_display: rank inverted so higher = more/richer
    bar_data = pd.DataFrame({
        "Volume (posts)"   : [s["volume_score"]           for s in scores],
        "Voice richness"   : [s["richness_score_display"] for s in scores],
    }, index=[f"C{s['cluster_id']}" for s in scores])
    st.bar_chart(bar_data, height=240, use_container_width=True)

    st.markdown(
        "<div style='font-size:0.72rem;color:#9A8F83;margin-top:-0.5rem;margin-bottom:1.2rem;'>"
        "Rank-based (1–5 scale). Taller bar = stronger in that dimension. "
        "Gap between bars = investment mismatch.</div>",
        unsafe_allow_html=True,
    )

    # Granite strategy brief
    with st.spinner("Generating strategic recommendation…"):
        try:
            brief = _get_strategy_brief(
                json.dumps(scores,   sort_keys=True),
                json.dumps(tensions, sort_keys=True),
                profile["brand_name"],
            )
        except Exception as exc:
            st.error(f"Strategy brief failed: {exc}")
            st.info("Make sure Ollama is running: `ollama serve`")
            brief = None

    if brief:
        st.markdown(
            f"<div class='diagnosis-card'>"
            f"<div class='diagnosis-label'>Strategic Recommendation</div>"
            f"<div style='font-size:0.9rem;line-height:1.65;'>{brief.get('strategic_brief', '')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        experiment = brief.get("experiment", "")
        if experiment:
            st.markdown(
                f"<div class='gap-card'>"
                f"<div class='diagnosis-label'>2-Week Experiment</div>"
                f"<div style='font-size:0.88rem;line-height:1.6;color:#5A4F44;'>"
                f"{experiment}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Underutilized / overused callout
        under_id = brief.get("underutilized_cluster")
        over_id  = brief.get("overused_cluster")
        if under_id is not None or over_id is not None:
            col_u, col_o = st.columns(2, gap="medium")
            with col_u:
                label = next(
                    (f"C{s['cluster_id']} {s['pillar']}" for s in scores if s["cluster_id"] == under_id),
                    f"C{under_id}" if under_id is not None else "—"
                )
                st.markdown(
                    f"<div class='diagnosis-card'>"
                    f"<div class='diagnosis-label'>Underutilized Territory</div>"
                    f"<div style='font-size:0.9rem;color:#5A8A6A;font-weight:600;'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_o:
                label = next(
                    (f"C{s['cluster_id']} {s['pillar']}" for s in scores if s["cluster_id"] == over_id),
                    f"C{over_id}" if over_id is not None else "—"
                )
                st.markdown(
                    f"<div class='diagnosis-card'>"
                    f"<div class='diagnosis-label'>Over-Invested Territory</div>"
                    f"<div style='font-size:0.9rem;color:#C4A35A;font-weight:600;'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    profile  = load_profile()
    clusters = load_clusters()
    render_sidebar(profile)

    st.markdown("## StyleSync")
    st.markdown(
        "<div style='color:#7A6F63;font-size:0.9rem;margin-top:-0.4rem;'>"
        "Creative Intelligence Platform for HotCakes Bakes</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    tab_create, tab_analyze, tab_discover = st.tabs(["Create", "Analyze", "Discover"])

    with tab_create:
        render_create_tab(profile)

    with tab_analyze:
        render_analyze_tab(profile)

    with tab_discover:
        render_discover_tab(profile, clusters)


if __name__ == "__main__":
    main()
