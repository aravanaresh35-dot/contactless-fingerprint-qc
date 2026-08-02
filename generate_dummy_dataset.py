"""
generate_dummy_dataset.py
==========================

Synthetic fingerprint-like image generator.

The assignment specification calls for 20 real smartphone captures (5 per
condition: good, blurry, dark, glare). Since this repository must run
end-to-end immediately without requiring physical hardware, this script
procedurally generates fingerprint-like ridge patterns and applies
controlled degradations (motion blur, underexposure, specular glare) to
populate ``test_dataset/`` with a representative dataset that exercises
every branch of the quality gate.

Run:
    python generate_dummy_dataset.py

Replace these with real smartphone captures before a production
evaluation -- synthetic ridge patterns are useful for pipeline validation
but are not a substitute for real acquisition-noise characteristics.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

OUTPUT_ROOT = "test_dataset"
IMAGE_SIZE = (480, 640)  # (height, width)
SEED = 42


def _make_ridge_pattern(
    size: tuple[int, int],
    frequency: float = 0.35,
    orientation_deg: float = 25.0,
    warp_strength: float = 6.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Procedurally synthesize a fingerprint-like oriented ridge pattern using
    a warped sinusoidal grating. This approximates the periodic
    ridge-valley structure of a real fingerprint closely enough to
    exercise the Gabor-based ridge clarity metric.
    """
    rng = rng or np.random.default_rng(SEED)
    height, width = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)

    theta = np.deg2rad(orientation_deg)
    # Smooth low-frequency warp field to mimic natural ridge curvature
    warp = warp_strength * np.sin(2 * np.pi * xx / width * 2 + rng.uniform(0, 2 * np.pi))

    projected = (xx * np.cos(theta) + yy * np.sin(theta)) + warp
    ridge = 0.5 + 0.5 * np.sin(2 * np.pi * projected * frequency / 10.0)

    # Elliptical vignette mask so the pattern resembles a finger silhouette
    cy, cx = height / 2.0, width / 2.0
    ellipse = ((xx - cx) ** 2) / (width * 0.34) ** 2 + ((yy - cy) ** 2) / (
        height * 0.42
    ) ** 2
    mask = np.clip(1.2 - ellipse, 0.0, 1.0)

    ridge_img = ridge * mask
    # Base skin tone with subtle texture noise
    noise = rng.normal(0, 0.02, size=size)
    combined = np.clip(0.25 + 0.55 * ridge_img + noise, 0.0, 1.0)

    gray = (combined * 255).astype(np.uint8)

    # Background outside the finger silhouette: neutral mid-gray surface
    background = np.full(size, 180, dtype=np.uint8)
    finger_alpha = (mask > 0.15).astype(np.uint8)
    final = np.where(finger_alpha == 1, gray, background)

    bgr = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)
    return bgr


def _apply_motion_blur(image: np.ndarray, kernel_size: int = 21) -> np.ndarray:
    """Simulate hand-shake motion blur via a linear motion kernel."""
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[kernel_size // 2, :] = 1.0
    kernel /= kernel_size
    return cv2.filter2D(image, -1, kernel)


def _apply_darkness(image: np.ndarray, factor: float = 0.22) -> np.ndarray:
    """Simulate underexposure by scaling pixel intensities down."""
    return np.clip(image.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def _apply_glare(
    image: np.ndarray, num_spots: int = 3, rng: np.random.Generator | None = None
) -> np.ndarray:
    """Simulate specular reflection glare with bright, near-saturated blobs."""
    rng = rng or np.random.default_rng(SEED)
    result = image.copy()
    height, width = image.shape[:2]
    for _ in range(num_spots):
        cx = rng.integers(int(width * 0.25), int(width * 0.75))
        cy = rng.integers(int(height * 0.25), int(height * 0.75))
        radius = rng.integers(45, 85)
        # Draw a near-fully-saturated disc directly (value 250) so it
        # reliably crosses the glare intensity threshold (> 240)
        # regardless of the underlying skin-tone value beneath it, then
        # feather the edge slightly with a light blur for realism.
        overlay = result.copy()
        cv2.circle(overlay, (cx, cy), radius, (250, 250, 250), -1)
        overlay = cv2.GaussianBlur(overlay, (9, 9), 0)
        result = cv2.addWeighted(overlay, 0.95, result, 0.05, 0)
    return result


def generate_dataset(output_root: str = OUTPUT_ROOT, per_category: int = 5) -> None:
    """Generate the full synthetic test dataset (4 categories x N images)."""
    categories = ("good", "blurry", "dark", "glare")
    for category in categories:
        os.makedirs(os.path.join(output_root, category), exist_ok=True)

    for i in range(1, per_category + 1):
        rng = np.random.default_rng(SEED + i)
        base = _make_ridge_pattern(
            IMAGE_SIZE,
            frequency=rng.uniform(0.28, 0.42),
            orientation_deg=rng.uniform(0, 60),
            rng=rng,
        )

        # --- Good capture: well-lit, sharp, centered ---------------------
        good_path = os.path.join(output_root, "good", f"good_{i:02d}.jpg")
        cv2.imwrite(good_path, base)

        # --- Blurry capture: strong motion blur --------------------------
        blurry = _apply_motion_blur(base, kernel_size=25)
        blurry_path = os.path.join(output_root, "blurry", f"blur_{i:02d}.jpg")
        cv2.imwrite(blurry_path, blurry)

        # --- Dark capture: severe underexposure ---------------------------
        dark = _apply_darkness(base, factor=0.20)
        dark_path = os.path.join(output_root, "dark", f"dark_{i:02d}.jpg")
        cv2.imwrite(dark_path, dark)

        # --- Glare capture: specular reflection blobs ---------------------
        glare = _apply_glare(base, num_spots=int(rng.integers(3, 5)), rng=rng)
        glare_path = os.path.join(output_root, "glare", f"glare_{i:02d}.jpg")
        cv2.imwrite(glare_path, glare)

    print(f"Synthetic dataset generated under '{output_root}/' "
          f"({per_category} images x 4 categories = {per_category * 4} total).")


if __name__ == "__main__":
    generate_dataset()
