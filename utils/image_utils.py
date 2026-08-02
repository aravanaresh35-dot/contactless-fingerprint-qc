"""
image_utils.py
===============

Low-level image I/O and preprocessing helper routines shared across the
quality-assessment pipeline.

These helpers deliberately avoid any business logic (thresholds, pass/fail
decisions, etc.) so that they can be reused by both the metric functions and
any future preprocessing stages without introducing coupling.
"""

from __future__ import annotations

import os
from typing import Union

import cv2
import numpy as np

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


class ImageLoadError(Exception):
    """Raised when an image cannot be located, read, or decoded."""


def load_image(image_path_or_array: Union[str, np.ndarray]) -> np.ndarray:
    """
    Load an image from disk or pass through an already-decoded array.

    Parameters
    ----------
    image_path_or_array : str | np.ndarray
        Either a filesystem path to an image file, or an already-decoded
        BGR ``numpy.ndarray`` (as returned by ``cv2.imread`` /
        ``cv2.imdecode``).

    Returns
    -------
    np.ndarray
        A 3-channel BGR image array.

    Raises
    ------
    ImageLoadError
        If the path does not exist, has an unsupported extension, or the
        file cannot be decoded into a valid image.
    """
    if isinstance(image_path_or_array, np.ndarray):
        img = image_path_or_array
    elif isinstance(image_path_or_array, str):
        if not os.path.isfile(image_path_or_array):
            raise ImageLoadError(f"File not found: {image_path_or_array}")

        ext = os.path.splitext(image_path_or_array)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ImageLoadError(
                f"Unsupported file extension '{ext}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )

        img = cv2.imread(image_path_or_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ImageLoadError(
                f"OpenCV failed to decode image: {image_path_or_array}"
            )
    else:
        raise ImageLoadError(
            f"Unsupported input type: {type(image_path_or_array)}. "
            "Expected a file path (str) or a numpy.ndarray."
        )

    if img.ndim == 2:
        # Grayscale image supplied directly -> convert to 3-channel BGR.
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if img.size == 0:
        raise ImageLoadError("Decoded image is empty.")

    return img


def to_grayscale(image_bgr: np.ndarray) -> np.ndarray:
    """Convert a BGR image to single-channel grayscale."""
    if image_bgr.ndim == 2:
        return image_bgr
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def resize_for_display(image_bgr: np.ndarray, max_dim: int = 800) -> np.ndarray:
    """
    Resize an image so that its largest dimension does not exceed
    ``max_dim``, preserving aspect ratio. Used only for UI display, never
    for metric computation (which should always run on the full-resolution
    capture).
    """
    height, width = image_bgr.shape[:2]
    largest = max(height, width)
    if largest <= max_dim:
        return image_bgr

    scale = max_dim / float(largest)
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image_bgr, new_size, interpolation=cv2.INTER_AREA)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, guarding against division by zero."""
    if denominator == 0:
        return default
    return numerator / denominator
