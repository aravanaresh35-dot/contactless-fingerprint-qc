"""
quality_assessment.py
======================

Public entry-point module for the Contactless Fingerprint Quality
Assessment & Scoring Pipeline.

This module re-exports the individual metric functions and the master
``quality_gate`` orchestrator from the ``utils`` package so that the
project can be used exactly as specified in the assignment brief, i.e.:

    from quality_assessment import quality_gate
    result = quality_gate("path/to/image.jpg")

Keeping this file as a thin facade (rather than duplicating logic) avoids
drift between the top-level API and the underlying modular implementation
in ``utils/``, which is where the real logic lives and is unit-testable in
isolation.
"""

from __future__ import annotations

from utils.guidance import resolve_guidance
from utils.metrics import (
    check_blur,
    check_brightness,
    check_glare,
    check_ridge_clarity,
    check_roi_completeness,
)
from utils.scoring import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    compute_composite_score,
    quality_gate,
)

__all__ = [
    "check_blur",
    "check_brightness",
    "check_glare",
    "check_roi_completeness",
    "check_ridge_clarity",
    "compute_composite_score",
    "quality_gate",
    "resolve_guidance",
    "DEFAULT_THRESHOLDS",
    "DEFAULT_WEIGHTS",
]


if __name__ == "__main__":
    # Simple manual smoke-test entry point:
    #   python quality_assessment.py path/to/image.jpg
    import sys
    import json

    if len(sys.argv) != 2:
        print("Usage: python quality_assessment.py <image_path>")
        sys.exit(1)

    try:
        result = quality_gate(sys.argv[1])
        print(json.dumps(result, indent=2))
    except ValueError as err:
        print(f"Error: {err}")
        sys.exit(1)
