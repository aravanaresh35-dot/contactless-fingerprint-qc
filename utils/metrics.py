"""
metrics.py
==========

Implements the five fundamental biometric image-quality metrics used by the
contactless fingerprint QC pipeline:

    1. Blur            -> Laplacian variance
    2. Brightness      -> Grayscale mean intensity
    3. Glare           -> Over-saturation pixel ratio
    4. ROI completeness-> Otsu thresholding + foreground area ratio
    5. Ridge clarity   -> Gabor filter response variance

Each function is self-contained, side-effect free, and returns a plain
``dict`` so results are trivially serializable (e.g. to CSV or JSON) and
easy to unit test in isolation.
"""

from __future__ import annotations

import cv2
import numpy as np

from .image_utils import to_grayscale


def check_blur(image_bgr: np.ndarray, threshold: float = 10.0) -> dict:
    """
    Detect blur using the variance of the Laplacian operator.

    A sharp image contains strong high-frequency edge content, which
    produces a high-variance Laplacian response. Blurred images suppress
    high-frequency content and therefore produce a low-variance response.

    Parameters
    ----------
    image_bgr : np.ndarray
        Input BGR image.
    threshold : float
        Minimum acceptable Laplacian variance. Below this, the image is
        flagged as blurry.

    Returns
    -------
    dict with keys: ``blur_score``, ``is_blurry``.
    """
    gray = to_grayscale(image_bgr)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return {
        "blur_score": round(blur_score, 2),
        "is_blurry": bool(blur_score < threshold),
    }


def check_brightness(
    image_bgr: np.ndarray,
    min_thresh: float = 50.0,
    max_thresh: float = 210.0,
) -> dict:
    """
    Assess exposure using the mean grayscale pixel intensity.

    Parameters
    ----------
    image_bgr : np.ndarray
        Input BGR image.
    min_thresh : float
        Mean intensity below this value is considered underexposed.
    max_thresh : float
        Mean intensity above this value is considered overexposed.

    Returns
    -------
    dict with keys: ``brightness``, ``too_dark``, ``too_bright``.
    """
    gray = to_grayscale(image_bgr)
    brightness = float(np.mean(gray))
    return {
        "brightness": round(brightness, 2),
        "too_dark": bool(brightness < min_thresh),
        "too_bright": bool(brightness > max_thresh),
    }


def check_glare(image_bgr: np.ndarray, max_glare_ratio: float = 0.05) -> dict:
    """
    Detect specular glare by measuring the fraction of near-saturated
    pixels (intensity > 240).

    Parameters
    ----------
    image_bgr : np.ndarray
        Input BGR image.
    max_glare_ratio : float
        Maximum acceptable fraction of saturated pixels.

    Returns
    -------
    dict with keys: ``glare_fraction``, ``has_glare``.
    """
    gray = to_grayscale(image_bgr)
    glare_pixels = int(np.sum(gray > 240))
    total_pixels = int(gray.size)
    glare_fraction = float(glare_pixels / total_pixels) if total_pixels else 0.0
    return {
        "glare_fraction": round(glare_fraction, 4),
        "has_glare": bool(glare_fraction > max_glare_ratio),
    }


def check_roi_completeness(
    image_bgr: np.ndarray, min_roi_ratio: float = 0.15
) -> dict:
    """
    Estimate the fraction of the frame occupied by the finger using Otsu's
    automatic thresholding on a blurred grayscale image.

    Parameters
    ----------
    image_bgr : np.ndarray
        Input BGR image.
    min_roi_ratio : float
        Minimum acceptable foreground-to-frame area ratio.

    Returns
    -------
    dict with keys: ``roi_fraction``, ``roi_complete``.
    """
    gray = to_grayscale(image_bgr)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Otsu can invert foreground/background depending on scene contrast.
    # Heuristic: the finger (foreground) is typically the minority class
    # when the capture guide is well framed, so pick whichever binary class
    # occupies less than half the frame -- this stabilizes the ratio across
    # both bright-background and dark-background captures.
    foreground_pixels = int(np.sum(thresh > 0))
    total_pixels = int(gray.size)
    fraction_white = foreground_pixels / total_pixels if total_pixels else 0.0

    if fraction_white > 0.5:
        roi_fraction = 1.0 - fraction_white
    else:
        roi_fraction = fraction_white

    return {
        "roi_fraction": round(float(roi_fraction), 4),
        "roi_complete": bool(roi_fraction >= min_roi_ratio),
    }


def check_ridge_clarity(image_bgr: np.ndarray, threshold: float = 15.0) -> dict:
    """
    Assess fingerprint ridge-valley clarity using a Gabor filter bank
    response variance. Ridge patterns are quasi-periodic and orientation
    selective, so a Gabor kernel tuned near the expected ridge frequency
    produces strong response variance on genuine ridge structure and a
    flat response on featureless or smooth skin.

    Parameters
    ----------
    image_bgr : np.ndarray
        Input BGR image.
    threshold : float
        Minimum acceptable ridge score.

    Returns
    -------
    dict with keys: ``ridge_score``, ``ridges_clear``.
    """
    gray = to_grayscale(image_bgr)

    # Average the response variance across four orientations (0, 45, 90,
    # 135 degrees) so that ridge clarity is not biased by finger rotation.
    orientations = (0, np.pi / 4, np.pi / 2, 3 * np.pi / 4)
    responses = []
    for theta in orientations:
        kernel = cv2.getGaborKernel(
            ksize=(21, 21),
            sigma=5.0,
            theta=theta,
            lambd=10.0,
            gamma=0.5,
            psi=0,
            ktype=cv2.CV_64F,
        )
        filtered = cv2.filter2D(gray, cv2.CV_64F, kernel)
        responses.append(np.var(filtered))

    ridge_score = float(np.mean(responses) / 100.0)

    return {
        "ridge_score": round(ridge_score, 2),
        "ridges_clear": bool(ridge_score >= threshold),
    }
