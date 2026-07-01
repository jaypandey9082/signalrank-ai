from __future__ import annotations

import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.sandbox_helpers import (
    DEMO_MAX_CANDIDATES,
    SandboxRunResult,
    candidate_preview_rows,
    cap_candidates_for_demo,
    load_demo_sample,
    parse_uploaded_candidate_file,
    run_demo_ranking,
    shorten_reasoning_for_table,
)
from src.ui_components import (
    cap_top_k_for_demo,
    inject_premium_css,
    render_empty_state,
    render_hero,
    render_methodology_cards,
    render_metric_card,
    render_section_header,
    render_sidebar_info,
    render_status_chip,
    render_validation_summary,
    score_badge,
)


st.set_page_config(
    page_title="SignalRank AI Sandbox",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def cached_demo_sample() -> list[dict]:
    return load_demo_sample()


def main() -> None:
    inject_premium_css()
    render_hero()

    with st.sidebar:
        render_sidebar_info(DEMO_MAX_CANDIDATES)
        st.markdown("#### Controls")
        top_k = st.slider("Top K", min_value=1, max_value=100, value=10)
        show_debug = st.checkbox("Show debug columns", value=False)
        show_validation_details = st.checkbox("Show validation details", value=True)
        load_sample = st.button("Load bundled demo sample", width="stretch")
        uploaded = st.file_uploader(
            "Upload candidate sample",
            type=["json", "jsonl", "gz"],
            accept_multiple_files=False,
        )
        st.warning("Do not upload the full 100K candidates file here. Use rank.py for full submission.")

    if "candidates" not in st.session_state or load_sample:
        st.session_state.candidates = cached_demo_sample()
        st.session_state.source_label = "Bundled demo sample"
        st.session_state.result = None

    if uploaded is not None:
        try:
            st.session_state.candidates = parse_uploaded_candidate_file(uploaded.name, uploaded.getvalue())
            st.session_state.source_label = uploaded.name
            st.session_state.result = None
        except ValueError as exc:
            st.error("Could not load candidate sample.")
            with st.expander("Debug details"):
                st.code(str(exc))
            return

    candidates = st.session_state.get("candidates", [])
    if not candidates:
        render_empty_state()
        return

    capped, cap_warnings = cap_candidates_for_demo(candidates, DEMO_MAX_CANDIDATES)
    effective_top_k, top_k_warning = cap_top_k_for_demo(top_k, len(capped))

    render_section_header(
        "Loaded Sample",
        "Review the input sample before running the deterministic demo ranker.",
    )
    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_metric_card("Source", st.session_state.get("source_label", "Bundled demo sample"), "Current input")
    with metric_cols[1]:
        render_metric_card("Loaded", len(candidates), "Candidates in file")
    with metric_cols[2]:
        render_metric_card("Processed", len(capped), f"Demo cap: {DEMO_MAX_CANDIDATES}")
    with metric_cols[3]:
        render_metric_card("Effective Top K", effective_top_k, "Rows returned")

    for warning in cap_warnings:
        st.warning(warning)
    if top_k_warning:
        st.warning(top_k_warning)

    st.dataframe(candidate_preview_rows(capped), width="stretch", hide_index=True)

    run_cols = st.columns([1, 2])
    with run_cols[0]:
        run_clicked = st.button("Run ranking demo", type="primary", width="stretch")
    with run_cols[1]:
        st.markdown(
            render_status_chip("CPU-only", "info")
            + " "
            + render_status_chip("No hosted LLM calls", "success")
            + " "
            + render_status_chip("Small sample mode", "neutral"),
            unsafe_allow_html=True,
        )

    if run_clicked:
        with st.spinner("Ranking sample and generating reasoning..."):
            try:
                st.session_state.result = run_demo_ranking(
                    candidates,
                    top_k=top_k,
                    max_candidates=DEMO_MAX_CANDIDATES,
                )
            except Exception as exc:  # noqa: BLE001 - UI should avoid raw stack traces by default.
                st.error("Ranking demo failed.")
                with st.expander("Debug details"):
                    st.code(repr(exc))
                return

    result: SandboxRunResult | None = st.session_state.get("result")
    if result is None:
        render_section_header("Ready to Rank", "Run the demo to generate ranked rows, reasoning, validation, and downloads.")
        render_empty_state()
        return

    render_section_header("Demo Run Summary", "The sandbox output is for review only; official final submission still uses the CLI.")
    summary_cols = st.columns(4)
    with summary_cols[0]:
        render_metric_card("Runtime", f"{result.elapsed_seconds:.2f}s", "Local deterministic run")
    with summary_cols[1]:
        render_metric_card("Rows", len(result.rows), "Demo output rows")
    with summary_cols[2]:
        render_metric_card("Errors", result.validation_error_count, "Internal validation")
    with summary_cols[3]:
        render_metric_card("Warnings", result.validation_warning_count + len(result.warnings), "Validation and run notes")

    if result.validation_is_valid:
        st.success("Ranking demo completed and internal validation passed.")
    else:
        st.error("Ranking demo completed, but internal validation found errors.")
    for warning in result.warnings:
        st.warning(warning)

    results_tab, reasoning_tab, validation_tab, downloads_tab, methodology_tab = st.tabs(
        ["Results", "Reasoning", "Validation", "Downloads", "Methodology"]
    )

    with results_tab:
        render_section_header("Ranked Results", "Canonical demo columns are candidate_id, rank, score, and reasoning.")
        result_metric_cols = st.columns(4)
        with result_metric_cols[0]:
            render_metric_card("Ranked candidates", len(result.rows), "Rows shown")
        with result_metric_cols[1]:
            top_score = result.rows[0]["score"] if result.rows else ""
            render_metric_card("Top score", top_score, "Highest demo score")
        with result_metric_cols[2]:
            render_metric_card("Runtime", f"{result.elapsed_seconds:.2f}s", "End-to-end demo")
        with result_metric_cols[3]:
            validation_label = "Valid" if result.validation_is_valid else "Errors"
            render_metric_card("Validation status", validation_label, "Internal checks")
        st.dataframe(_table_rows(result.rows, result.debug_rows, show_debug), width="stretch", hide_index=True)

    with reasoning_tab:
        render_section_header("Candidate Reasoning", "Factual explanations generated from extracted candidate evidence.")
        for row in result.rows:
            st.markdown(
                f"""
<div class="sr-result-card">
  <h3>#{int(row['rank'])} {escape(str(row['candidate_id']))} &nbsp; {score_badge(float(row['score']))}</h3>
  <p>{escape(str(row['reasoning']))}</p>
</div>
                """,
                unsafe_allow_html=True,
            )

    with validation_tab:
        render_section_header("Validation", "Checks column shape, row count, ranks, score ordering, IDs, and reasoning quality.")
        render_validation_summary(
            result.validation_is_valid,
            result.validation_error_count,
            result.validation_warning_count,
        )
        st.markdown(result.validation_markdown)
        if show_validation_details:
            with st.expander("Plain-text validation details", expanded=False):
                st.code(result.validation_text)

    with downloads_tab:
        render_section_header("Downloads", "CSV and XLSX are generated from the same ranked rows.")
        download_cols = st.columns(3)
        with download_cols[0]:
            st.download_button(
                "Download ranked CSV",
                data=result.csv_bytes,
                file_name="signalrank_demo_submission.csv",
                mime="text/csv",
                width="stretch",
            )
        with download_cols[1]:
            st.download_button(
                "Download ranked XLSX",
                data=result.xlsx_bytes,
                file_name="signalrank_demo_submission.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with download_cols[2]:
            st.download_button(
                "Download demo report",
                data=result.report_markdown.encode("utf-8"),
                file_name="signalrank_demo_report.md",
                mime="text/markdown",
                width="stretch",
            )
        st.markdown(result.report_markdown)

    with methodology_tab:
        render_section_header("Methodology", "The sandbox is a thin UI around the same deterministic backend used by the CLI.")
        render_methodology_cards()
        st.markdown(
            """
### Full submission remains command-line based

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Optional portal XLSX/report command:

```bash
python generate_submission.py --candidates ./candidates.jsonl --out ./outputs/submission.csv --xlsx ./outputs/submission.xlsx --report-out ./outputs/submission_run_report.md
```

The full dataset is not included in the repo, and this sandbox should not be used for the 100K final run.

Full ranking uses `rank.py` from the command line. The sandbox is intentionally capped to small samples.
            """
        )


def _table_rows(rows: list[dict], debug_rows: list[dict], show_debug: bool) -> list[dict]:
    debug_by_id = {row.get("candidate_id"): row for row in debug_rows}
    table = []
    for row in rows:
        table_row = {
            "rank": row["rank"],
            "candidate_id": row["candidate_id"],
            "score": row["score"],
            "score_band": _score_band_text(float(row["score"])),
            "reasoning": shorten_reasoning_for_table(row["reasoning"]),
        }
        if show_debug:
            debug = debug_by_id.get(row["candidate_id"], {})
            table_row.update(
                {
                    "title": debug.get("title", ""),
                    "years_of_experience": debug.get("years_of_experience", ""),
                    "location": debug.get("location", ""),
                    "static_fit_score": debug.get("static_fit_score", ""),
                    "redrob_availability_score": debug.get("redrob_availability_score", ""),
                    "trap_total_penalty": debug.get("trap_total_penalty", ""),
                    "applied_cap_codes": debug.get("applied_cap_codes", ""),
                }
            )
        table.append(table_row)
    return table


def _score_band_text(score: float) -> str:
    if score >= 0.80:
        return "elite"
    if score >= 0.70:
        return "strong"
    if score >= 0.58:
        return "good"
    if score >= 0.42:
        return "borderline"
    return "weak"


if __name__ == "__main__":
    main()
