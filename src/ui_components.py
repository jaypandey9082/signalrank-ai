from __future__ import annotations

from html import escape

import streamlit as st


def inject_premium_css() -> None:
    st.markdown(
        """
<style>
:root {
  --sr-bg: #f8fafc;
  --sr-panel: #ffffff;
  --sr-panel-soft: #f1f5f9;
  --sr-border: #dbe5f0;
  --sr-border-strong: #cbd5e1;
  --sr-text: #0f172a;
  --sr-muted: #64748b;
  --sr-blue: #2563eb;
  --sr-blue-soft: #dbeafe;
  --sr-green: #047857;
  --sr-green-soft: #d1fae5;
  --sr-amber: #b45309;
  --sr-amber-soft: #fef3c7;
  --sr-red: #b91c1c;
  --sr-red-soft: #fee2e2;
  --sr-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

html, body, [class*="css"] {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 28rem),
    var(--sr-bg);
  color: var(--sr-text);
}

.main .block-container {
  max-width: 1180px;
  padding-top: 2.1rem;
  padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--sr-border);
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  gap: 0.85rem;
}

.sr-hero {
  background: linear-gradient(135deg, #ffffff 0%, #eef6ff 100%);
  border: 1px solid var(--sr-border);
  border-radius: 24px;
  padding: 30px 34px;
  box-shadow: var(--sr-shadow);
  margin-bottom: 1.25rem;
}

.sr-eyebrow {
  color: var(--sr-blue);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 0.45rem;
}

.sr-hero h1 {
  color: var(--sr-text);
  font-size: 2.35rem;
  line-height: 1.08;
  margin: 0 0 0.6rem 0;
  letter-spacing: 0;
}

.sr-hero p {
  color: var(--sr-muted);
  font-size: 1.02rem;
  line-height: 1.6;
  max-width: 820px;
  margin: 0;
}

.sr-hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 1rem;
}

.sr-card {
  background: var(--sr-panel);
  border: 1px solid var(--sr-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.055);
}

.sr-metric-card {
  min-height: 112px;
}

.sr-metric-label {
  color: var(--sr-muted);
  font-size: 0.78rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.sr-metric-value {
  color: var(--sr-text);
  font-size: 1.7rem;
  font-weight: 850;
  line-height: 1.2;
  margin-top: 0.4rem;
}

.sr-metric-helper {
  color: var(--sr-muted);
  font-size: 0.88rem;
  margin-top: 0.35rem;
}

.sr-section-header {
  margin: 1.4rem 0 0.7rem 0;
}

.sr-section-header h2 {
  color: var(--sr-text);
  font-size: 1.22rem;
  margin: 0;
  letter-spacing: 0;
}

.sr-section-header p {
  color: var(--sr-muted);
  margin: 0.25rem 0 0 0;
  line-height: 1.5;
}

.sr-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.28rem 0.62rem;
  font-size: 0.78rem;
  font-weight: 760;
  border: 1px solid transparent;
  white-space: nowrap;
}

.sr-chip-success { color: var(--sr-green); background: var(--sr-green-soft); border-color: #a7f3d0; }
.sr-chip-warning { color: var(--sr-amber); background: var(--sr-amber-soft); border-color: #fde68a; }
.sr-chip-danger { color: var(--sr-red); background: var(--sr-red-soft); border-color: #fecaca; }
.sr-chip-info { color: #1d4ed8; background: var(--sr-blue-soft); border-color: #bfdbfe; }
.sr-chip-neutral { color: #475569; background: var(--sr-panel-soft); border-color: var(--sr-border-strong); }

.sr-result-card {
  background: var(--sr-panel);
  border: 1px solid var(--sr-border);
  border-radius: 18px;
  padding: 17px 18px;
  margin-bottom: 0.8rem;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.045);
}

.sr-result-card h3 {
  font-size: 1rem;
  margin: 0 0 0.55rem 0;
  letter-spacing: 0;
}

.sr-result-card p {
  color: #334155;
  margin: 0.55rem 0 0 0;
  line-height: 1.55;
}

.sr-empty {
  border: 1px dashed var(--sr-border-strong);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  padding: 28px;
  color: var(--sr-muted);
  text-align: center;
}

.sr-method-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
  margin-top: 0.6rem;
}

.sr-method-card h3 {
  font-size: 0.98rem;
  margin: 0 0 0.45rem 0;
}

.sr-method-card p {
  color: var(--sr-muted);
  font-size: 0.9rem;
  line-height: 1.52;
  margin: 0;
}

.stButton > button,
.stDownloadButton > button {
  border-radius: 12px;
  border: 1px solid var(--sr-border-strong);
  font-weight: 760;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
  background: var(--sr-blue);
  border-color: var(--sr-blue);
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--sr-border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
}

@media (max-width: 900px) {
  .sr-hero {
    padding: 24px;
  }
  .sr-hero h1 {
    font-size: 1.85rem;
  }
  .sr-method-grid {
    grid-template-columns: 1fr;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
<div class="sr-hero">
  <div class="sr-eyebrow">Candidate discovery sandbox</div>
  <h1>SignalRank AI</h1>
  <p><strong>Explainable candidate ranking for the Senior AI Engineer role.</strong></p>
  <p>Ranks candidates using career evidence, Redrob behavior signals, trap checks, and factual reasoning.</p>
  <div class="sr-hero-pills">
    <span class="sr-chip sr-chip-info">CPU-only</span>
    <span class="sr-chip sr-chip-success">No API calls</span>
    <span class="sr-chip sr-chip-neutral">Explainable</span>
    <span class="sr-chip sr-chip-neutral">CSV/XLSX output</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_info(max_candidates: int) -> None:
    st.markdown(
        f"""
<div class="sr-card">
  <div class="sr-eyebrow">Small-sample sandbox</div>
  <p style="margin:0;color:#475569;line-height:1.55;">
    Processes up to <strong>{int(max_candidates)}</strong> candidates locally. Use <code>rank.py</code>
    for full 100K submission runs. Do not upload the full candidates file here.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: object, helper: str = "") -> None:
    helper_html = f'<div class="sr-metric-helper">{escape(str(helper))}</div>' if helper else ""
    st.markdown(
        f"""
<div class="sr-card sr-metric-card">
  <div class="sr-metric-label">{escape(str(label))}</div>
  <div class="sr-metric-value">{escape(str(value))}</div>
  {helper_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_status_chip(label: str, kind: str = "neutral") -> str:
    allowed = {"success", "warning", "danger", "info", "neutral"}
    chip_kind = kind if kind in allowed else "neutral"
    return f'<span class="sr-chip sr-chip-{chip_kind}">{escape(str(label))}</span>'


def render_section_header(title: str, caption: str = "") -> None:
    caption_html = f"<p>{escape(caption)}</p>" if caption else ""
    st.markdown(
        f"""
<div class="sr-section-header">
  <h2>{escape(title)}</h2>
  {caption_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
<div class="sr-empty">
  Load the bundled demo sample or upload a JSON/JSONL candidate sample to begin.
</div>
        """,
        unsafe_allow_html=True,
    )


def render_validation_summary(is_valid: bool, error_count: int, warning_count: int) -> None:
    kind = "success" if is_valid else "danger"
    label = "Validation passed" if is_valid else "Validation failed"
    st.markdown(
        f"""
<div class="sr-card">
  <div class="sr-metric-label">Validation status</div>
  <div style="margin-top:0.7rem;">
    {render_status_chip(label, kind)}
    {render_status_chip(f"{error_count} errors", "danger" if error_count else "neutral")}
    {render_status_chip(f"{warning_count} warnings", "warning" if warning_count else "neutral")}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_methodology_cards() -> None:
    cards = [
        (
            "Static fit",
            "Career history, retrieval/ranking evidence, AI engineering skills, experience, and role alignment.",
        ),
        (
            "Redrob behavior",
            "Availability, responsiveness, logistics, reliability, trust, and market signals as a narrow multiplier.",
        ),
        (
            "Trap defense",
            "Penalty checks for wrong-role keyword stuffing, weak AI hype, inconsistent profiles, and low availability.",
        ),
        (
            "Evidence reasoning",
            "Deterministic explanations built from extracted candidate facts rather than hosted LLM calls.",
        ),
    ]
    card_html = "\n".join(
        f"""
<div class="sr-card sr-method-card">
  <h3>{escape(title)}</h3>
  <p>{escape(copy)}</p>
</div>
        """
        for title, copy in cards
    )
    st.markdown(f'<div class="sr-method-grid">{card_html}</div>', unsafe_allow_html=True)


def score_badge(score: float) -> str:
    value = float(score)
    if value >= 0.80:
        label, kind = "elite", "success"
    elif value >= 0.70:
        label, kind = "strong", "success"
    elif value >= 0.58:
        label, kind = "good", "info"
    elif value >= 0.42:
        label, kind = "borderline", "warning"
    else:
        label, kind = "weak", "danger"
    return render_status_chip(f"{label} {value:.3f}", kind)


def cap_top_k_for_demo(selected_top_k: int, loaded_count: int) -> tuple[int, str | None]:
    selected = max(1, int(selected_top_k))
    loaded = max(0, int(loaded_count))
    if loaded == 0:
        return 1, "No candidates are loaded yet, so Top K will be available after loading a sample."
    if selected > loaded:
        return loaded, f"Only {loaded} candidates loaded, so Top K was capped to {loaded} for this demo."
    return selected, None
