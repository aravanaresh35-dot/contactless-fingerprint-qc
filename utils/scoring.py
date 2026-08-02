"""
scoring.py
==========

Normalization and composite-score computation for the fingerprint QC
pipeline, plus the master ``quality_gate`` orchestration function.

Design notes
------------
Each raw metric lives on a different numeric scale (e.g. Laplacian variance
can range into the thousands, while glare fraction is bounded in [0, 1]).
Before the metrics can be combined into a single interpretable 0-100 score,
each is independently normalized into the [0, 1] range and then combined
via a weighted sum. Weights are configurable but default to the values
specified in the assignment brief.
"""

from __future__ import annotations

from typing import Optional

from . import metrics
from .guidance import resolve_guidance
from .image_utils import load_image

# Default weights for the composite score. Must sum to 1.0.
DEFAULT_WEIGHTS = {
    "blur": 0.25,
    "brightness": 0.15,
    "glare": 0.15,
    "roi": 0.20,
    "ridge": 0.25,
}

# Default thresholds for each metric / normalization target.
DEFAULT_THRESHOLDS = {
    "blur_threshold": 10.0,
    "blur_norm_cap": 50.0,      # Laplacian variance considered "fully sharp"
    "brightness_min": 50.0,
    "brightness_max": 210.0,
    "brightness_ideal": 128.0,
    "glare_max_ratio": 0.05,
    "roi_min_ratio": 0.15,
    "roi_norm_cap": 0.35,       # ROI fraction considered "fully framed"
    "ridge_threshold": 15.0,
    "ridge_norm_cap": 30.0,     # Ridge score considered "fully clear"
    "pass_score": 60.0,
}


def _normalize_blur(blur_score: float, cap: float) -> float:
    """Map raw Laplacian variance onto [0, 1]."""
    return min(1.0, max(0.0, blur_score / cap)) if cap else 0.0


def _normalize_brightness(brightness: float, ideal: float) -> float:
    """Map mean intensity onto [0, 1], peaking at the ideal value."""
    return max(0.0, 1.0 - abs(brightness - ideal) / ideal) if ideal else 0.0


def _normalize_glare(glare_fraction: float, max_ratio: float) -> float:
    """Map glare fraction onto [0, 1] (inverted -- less glare is better)."""
    return max(0.0, 1.0 - (glare_fraction / max_ratio)) if max_ratio else 0.0


def _normalize_roi(roi_fraction: float, cap: float) -> float:
    """Map ROI fraction onto [0, 1]."""
    return min(1.0, max(0.0, roi_fraction / cap)) if cap else 0.0


def _normalize_ridge(ridge_score: float, cap: float) -> float:
    """Map ridge clarity score onto [0, 1]."""
    return min(1.0, max(0.0, ridge_score / cap)) if cap else 0.0


def compute_composite_score(
    blur_res: dict,
    bright_res: dict,
    glare_res: dict,
    roi_res: dict,
    ridge_res: dict,
    weights: Optional[dict] = None,
    thresholds: Optional[dict] = None,
) -> dict:
    """
    Normalize the five raw metric results and combine them into a single
    weighted composite score in the range [0, 100].

    Returns
    -------
    dict
        ``composite_score`` (float, 0-100) and the individual normalized
        sub-scores (each in [0, 1]) for transparency / debugging.
    """
    weights = weights or DEFAULT_WEIGHTS
    thresholds = thresholds or DEFAULT_THRESHOLDS

    n_blur = _normalize_blur(blur_res["blur_score"], thresholds["blur_norm_cap"])
    n_bright = _normalize_brightness(
        bright_res["brightness"], thresholds["brightness_ideal"]
    )
    n_glare = _normalize_glare(
        glare_res["glare_fraction"], thresholds["glare_max_ratio"]
    )
    n_roi = _normalize_roi(roi_res["roi_fraction"], thresholds["roi_norm_cap"])
    n_ridge = _normalize_ridge(ridge_res["ridge_score"], thresholds["ridge_norm_cap"])

    weighted_sum = (
        weights["blur"] * n_blur
        + weights["brightness"] * n_bright
        + weights["glare"] * n_glare
        + weights["roi"] * n_roi
        + weights["ridge"] * n_ridge
    )
    composite_score = round(weighted_sum * 100.0, 1)

    return {
        "composite_score": composite_score,
        "normalized": {
            "blur": round(n_blur, 4),
            "brightness": round(n_bright, 4),
            "glare": round(n_glare, 4),
            "roi": round(n_roi, 4),
            "ridge": round(n_ridge, 4),
        },
    }


def quality_gate(
    image_path_or_array,
    thresholds: Optional[dict] = None,
    weights: Optional[dict] = None,
) -> dict:
    """
    Master Quality Control pipeline.

    Executes all five metric checks against an input image, computes the
    normalized composite score, evaluates hard pass/fail gating logic, and
    resolves a single human-readable guidance message.

    Parameters
    ----------
    image_path_or_array : str | np.ndarray
        Path to an image file, or an already-decoded BGR image array.
    thresholds : dict, optional
        Overrides for any key in ``DEFAULT_THRESHOLDS``.
    weights : dict, optional
        Overrides for any key in ``DEFAULT_WEIGHTS``. Must sum to 1.0.

    Returns
    -------
    dict
        Full structured result: ``passed``, ``composite_score``, per-metric
        sub-results, and ``guidance``.

    Raises
    ------
    ValueError
        If the image cannot be loaded/decoded.
    """
    merged_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    merged_weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    try:
        img = load_image(image_path_or_array)
    except Exception as exc:  # noqa: BLE001 - re-raised with clear context
        raise ValueError(f"Invalid image file or array: {exc}") from exc

    # --- Run all five metric checks -------------------------------------
    blur_res = metrics.check_blur(img, threshold=merged_thresholds["blur_threshold"])
    bright_res = metrics.check_brightness(
        img,
        min_thresh=merged_thresholds["brightness_min"],
        max_thresh=merged_thresholds["brightness_max"],
    )
    glare_res = metrics.check_glare(
        img, max_glare_ratio=merged_thresholds["glare_max_ratio"]
    )
    roi_res = metrics.check_roi_completeness(
        img, min_roi_ratio=merged_thresholds["roi_min_ratio"]
    )
    ridge_res = metrics.check_ridge_clarity(
        img, threshold=merged_thresholds["ridge_threshold"]
    )

    # --- Composite score --------------------------------------------------
    score_res = compute_composite_score(
        blur_res,
        bright_res,
        glare_res,
        roi_res,
        ridge_res,
        weights=merged_weights,
        thresholds=merged_thresholds,
    )
    composite_score = score_res["composite_score"]

    # --- Hard failure gating ----------------------------------------------
    has_hard_failure = (
        blur_res["is_blurry"]
        or bright_res["too_dark"]
        or bright_res["too_bright"]
        or glare_res["has_glare"]
        or not roi_res["roi_complete"]
        or not ridge_res["ridges_clear"]
    )

    passed = bool(
        composite_score >= merged_thresholds["pass_score"] and not has_hard_failure
    )

    guidance = resolve_guidance(blur_res, bright_res, glare_res, roi_res, ridge_res)

    return {
        "passed": passed,
        "composite_score": composite_score,
        "normalized_scores": score_res["normalized"],
        "blur": blur_res,
        "brightness": bright_res,
        "glare": glare_res,
        "roi": roi_res,
        "ridge": ridge_res,
        "guidance": guidance,
        "thresholds_used": merged_thresholds,
        "weights_used": merged_weights,
    }
