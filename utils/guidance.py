"""
guidance.py
===========

Resolves a single, prioritized, human-readable guidance message from the
raw per-metric results. Only one message is ever shown at a time so that
the user is not overwhelmed with simultaneous corrective instructions --
the checks are evaluated in a fixed priority order matching the assignment
specification's guidance matrix.
"""

from __future__ import annotations

GUIDANCE_MESSAGES = {
    "blurry": "Image is too blurry. Hold your camera steady and re-focus.",
    "too_dark": "Lighting is too dark. Turn on your flash or move to a lit area.",
    "too_bright": "Image is overexposed. Move away from direct bright light.",
    "glare": "Glare detected on finger. Tilt phone slightly to eliminate reflection.",
    "roi_incomplete": "Finger too far or incomplete. Move finger closer to fill the frame.",
    "ridges_unclear": "Ridge structure unclear. Clean camera lens or adjust lighting.",
    "good": "Good capture — ready for processing.",
}


def resolve_guidance(
    blur_res: dict,
    bright_res: dict,
    glare_res: dict,
    roi_res: dict,
    ridge_res: dict,
) -> str:
    """
    Determine the single most relevant guidance message given the results
    of all five quality checks.

    Priority order (first failing condition wins):
        1. Blur
        2. Too dark
        3. Too bright
        4. Glare
        5. ROI incompleteness
        6. Ridge clarity
        7. All passed -> "good capture" message

    Parameters
    ----------
    blur_res, bright_res, glare_res, roi_res, ridge_res : dict
        Results returned by the corresponding functions in ``metrics.py``.

    Returns
    -------
    str
        The resolved guidance message.
    """
    if blur_res["is_blurry"]:
        return GUIDANCE_MESSAGES["blurry"]
    if bright_res["too_dark"]:
        return GUIDANCE_MESSAGES["too_dark"]
    if bright_res["too_bright"]:
        return GUIDANCE_MESSAGES["too_bright"]
    if glare_res["has_glare"]:
        return GUIDANCE_MESSAGES["glare"]
    if not roi_res["roi_complete"]:
        return GUIDANCE_MESSAGES["roi_incomplete"]
    if not ridge_res["ridges_clear"]:
        return GUIDANCE_MESSAGES["ridges_unclear"]
    return GUIDANCE_MESSAGES["good"]
