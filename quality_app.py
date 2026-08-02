"""
quality_app.py
===============

Streamlit dashboard for the Contactless Fingerprint Quality Control
System.

Provides:
    * Sidebar sliders for live, dynamic threshold tuning.
    * Drag-and-drop image upload.
    * A prominent composite score readout (green / red).
    * Per-metric PASS / FAIL breakdown cards.
    * A guidance banner with corrective instructions.
    * An optional batch-preview mode over the bundled test dataset.

Run with:
    streamlit run quality_app.py
"""

from __future__ import annotations

import time

import cv2
import numpy as np
import streamlit as st

from quality_assessment import quality_gate

# --------------------------------------------------------------------------
# Page configuration & global styling
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Fingerprint QC Gate",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .main {
        background-color: #0e1117;
    }
    .qc-header {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .qc-subheader {
        color: #9aa4b2;
        font-size: 1.0rem;
        margin-bottom: 1.4rem;
    }
    .metric-card {
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(255,255,255,0.08);
        background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    }
    .metric-pass {
        border-left: 4px solid #22c55e;
    }
    .metric-fail {
        border-left: 4px solid #ef4444;
    }
    .metric-title {
        font-weight: 600;
        font-size: 0.95rem;
    }
    .metric-value {
        color: #9aa4b2;
        font-size: 0.85rem;
    }
    .score-pill {
        display: inline-block;
        padding: 0.6rem 1.4rem;
        border-radius: 999px;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    .score-pill-pass {
        background: rgba(34, 197, 94, 0.14);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.35);
    }
    .score-pill-fail {
        background: rgba(239, 68, 68, 0.14);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .guidance-banner {
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        font-size: 1.0rem;
        font-weight: 500;
        margin-top: 0.6rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    '<div class="qc-header">📱 Contactless Fingerprint Quality Control System</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="qc-subheader">Automated pre-flight image quality gate for '
    "mobile contactless biometric capture pipelines.</div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar: dynamic threshold tuning
# --------------------------------------------------------------------------
st.sidebar.header("⚙️ QC Threshold Settings")
st.sidebar.caption("Adjust thresholds live to see how the gate decision reacts.")

blur_threshold = st.sidebar.slider(
    "Blur threshold (Laplacian variance)", 5.0, 50.0, 10.0, step=0.5
)
min_brightness = st.sidebar.slider("Min brightness", 10, 100, 50, step=1)
max_brightness = st.sidebar.slider("Max brightness", 150, 255, 210, step=1)
max_glare_ratio = st.sidebar.slider(
    "Max glare fraction", 0.01, 0.20, 0.05, step=0.01
)
min_roi_ratio = st.sidebar.slider("Min ROI fraction", 0.05, 0.50, 0.15, step=0.01)
ridge_threshold = st.sidebar.slider("Ridge clarity threshold", 1.0, 40.0, 15.0, step=0.5)
pass_score = st.sidebar.slider("Composite pass score", 0.0, 100.0, 60.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.header("⚖️ Composite Score Weights")
w_blur = st.sidebar.slider("Weight: blur", 0.0, 1.0, 0.25, step=0.05)
w_bright = st.sidebar.slider("Weight: brightness", 0.0, 1.0, 0.15, step=0.05)
w_glare = st.sidebar.slider("Weight: glare", 0.0, 1.0, 0.15, step=0.05)
w_roi = st.sidebar.slider("Weight: ROI", 0.0, 1.0, 0.20, step=0.05)
w_ridge = st.sidebar.slider("Weight: ridge", 0.0, 1.0, 0.25, step=0.05)

weight_sum = w_blur + w_bright + w_glare + w_roi + w_ridge
if weight_sum > 0:
    normalized_weights = {
        "blur": w_blur / weight_sum,
        "brightness": w_bright / weight_sum,
        "glare": w_glare / weight_sum,
        "roi": w_roi / weight_sum,
        "ridge": w_ridge / weight_sum,
    }
else:
    normalized_weights = None

if abs(weight_sum - 1.0) > 1e-6:
    st.sidebar.caption(f"Weights sum to {weight_sum:.2f} → auto-normalized to 1.0.")

thresholds = {
    "blur_threshold": blur_threshold,
    "brightness_min": float(min_brightness),
    "brightness_max": float(max_brightness),
    "glare_max_ratio": max_glare_ratio,
    "roi_min_ratio": min_roi_ratio,
    "ridge_threshold": ridge_threshold,
    "pass_score": pass_score,
}

# --------------------------------------------------------------------------
# Main panel: image upload
# --------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload a fingerprint capture", type=["jpg", "jpeg", "png"]
)


def render_metric_card(title: str, passed: bool, value_str: str) -> str:
    """Build the HTML for a single metric breakdown card."""
    css_class = "metric-pass" if passed else "metric-fail"
    icon = "✅" if passed else "❌"
    return (
        f'<div class="metric-card {css_class}">'
        f'<div class="metric-title">{icon} {title}</div>'
        f'<div class="metric-value">{value_str}</div>'
        f"</div>"
    )


if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image_bgr is None:
        st.error("Could not decode the uploaded file. Please upload a valid JPG/PNG image.")
    else:
        start = time.perf_counter()
        try:
            res = quality_gate(image_bgr, thresholds=thresholds, weights=normalized_weights)
        except ValueError as exc:
            st.error(f"Processing error: {exc}")
            res = None
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        if res is not None:
            col1, col2 = st.columns([1, 1.2])

            with col1:
                st.image(
                    cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB),
                    caption="Uploaded capture",
                     use_column_width=True,
                )
                st.caption(f"Pipeline latency: {elapsed_ms} ms (budget: 300 ms)")

            with col2:
                score = res["composite_score"]
                pill_class = "score-pill-pass" if res["passed"] else "score-pill-fail"
                status_text = "PASSED" if res["passed"] else "REJECTED"
                st.markdown(
                    f'<span class="score-pill {pill_class}">'
                    f"{score} / 100 — {status_text}</span>",
                    unsafe_allow_html=True,
                )

                banner_bg = "rgba(34,197,94,0.12)" if res["passed"] else "rgba(239,68,68,0.12)"
                banner_color = "#22c55e" if res["passed"] else "#ef4444"
                st.markdown(
                    f'<div class="guidance-banner" '
                    f'style="background:{banner_bg};color:{banner_color};">'
                    f'💬 {res["guidance"]}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("#### Quality checks breakdown")

                st.markdown(
                    render_metric_card(
                        "Blur",
                        not res["blur"]["is_blurry"],
                        f"Laplacian variance: {res['blur']['blur_score']}"
                        f" (threshold ≥ {blur_threshold})",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    render_metric_card(
                        "Brightness",
                        not (res["brightness"]["too_dark"] or res["brightness"]["too_bright"]),
                        f"Mean intensity: {res['brightness']['brightness']}"
                        f" (range {min_brightness}–{max_brightness})",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    render_metric_card(
                        "Glare",
                        not res["glare"]["has_glare"],
                        f"Saturated pixel ratio: {res['glare']['glare_fraction']}"
                        f" (threshold ≤ {max_glare_ratio})",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    render_metric_card(
                        "ROI completeness",
                        res["roi"]["roi_complete"],
                        f"Finger area ratio: {res['roi']['roi_fraction']}"
                        f" (threshold ≥ {min_roi_ratio})",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    render_metric_card(
                        "Ridge clarity",
                        res["ridge"]["ridges_clear"],
                        f"Gabor response score: {res['ridge']['ridge_score']}"
                        f" (threshold ≥ {ridge_threshold})",
                    ),
                    unsafe_allow_html=True,
                )

            with st.expander("Raw JSON result"):
                st.json(res)
else:
    st.info("⬆️ Upload a fingerprint image to run it through the QC gate.")

st.markdown("---")

# --------------------------------------------------------------------------
# Optional: batch preview over the bundled synthetic/test dataset
# --------------------------------------------------------------------------
with st.expander("📊 Run batch evaluation over test_dataset/"):
    st.caption(
        "Evaluates every image bundled in the test_dataset/ folder using the "
        "current sidebar thresholds and displays a summary table."
    )
    if st.button("Run batch evaluation"):
        import glob
        import os

        import pandas as pd

        image_paths = sorted(
            glob.glob(os.path.join("test_dataset", "*", "*.jpg"))
            + glob.glob(os.path.join("test_dataset", "*", "*.png"))
        )

        if not image_paths:
            st.warning(
                "No images found in test_dataset/. Run "
                "`python generate_dummy_dataset.py` first."
            )
        else:
            rows = []
            progress = st.progress(0)
            for idx, path in enumerate(image_paths):
                category = os.path.basename(os.path.dirname(path))
                try:
                    result = quality_gate(path, thresholds=thresholds, weights=normalized_weights)
                    rows.append(
                        {
                            "File": os.path.basename(path),
                            "Category": category,
                            "Passed": result["passed"],
                            "Score": result["composite_score"],
                            "Guidance": result["guidance"],
                        }
                    )
                except ValueError as exc:
                    rows.append(
                        {
                            "File": os.path.basename(path),
                            "Category": category,
                            "Passed": False,
                            "Score": 0.0,
                            "Guidance": f"ERROR: {exc}",
                        }
                    )
                progress.progress((idx + 1) / len(image_paths))

            results_df = pd.DataFrame(rows)
            st.dataframe(results_df, use_container_width=True)

            pass_rate = 100.0 * results_df["Passed"].mean()
            st.metric("Overall pass rate", f"{pass_rate:.1f}%")

st.markdown(
    '<div style="text-align:center; color:#5b6472; font-size:0.8rem; '
    'margin-top:2rem;">Contactless Fingerprint QC Pipeline · Assignment 4</div>',
    unsafe_allow_html=True,
)
