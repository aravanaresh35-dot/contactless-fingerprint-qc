# Algorithmic Explanation

This document explains the algorithmic reasoning behind each of the five
quality metrics implemented in `utils/metrics.py`, and how they are
combined by `utils/scoring.py`.

## 1. Blur Detection — Laplacian Variance

**Idea:** Sharp edges contain high-frequency intensity changes. The
Laplacian operator is a second-derivative edge detector — applying it to a
sharp image produces large positive and negative responses concentrated
around edges, giving high variance across the response map. A blurred
image smooths those transitions, collapsing the Laplacian response toward
zero everywhere and producing low variance.

**Algorithm:**
1. Convert the image to grayscale.
2. Convolve with the discrete Laplacian kernel via `cv2.Laplacian`.
3. Compute the variance of the resulting response map.
4. Compare against a calibrated threshold (default `10.0`).

**Why variance and not mean?** The Laplacian response has a mean near zero
everywhere (positive and negative responses cancel), so the *magnitude of
spread* (variance), not the average value, is what distinguishes sharp
from blurry content.

## 2. Brightness Assessment — Mean Intensity

**Idea:** Exposure quality is well approximated by the arithmetic mean of
grayscale pixel intensity across the frame — a computationally trivial but
effective proxy for global exposure.

**Algorithm:**
1. Convert to grayscale.
2. Compute `mean(I_gray)`.
3. Flag `too_dark` if the mean falls below the lower bound (default `50`)
   and `too_bright` if it exceeds the upper bound (default `210`).

**Limitation:** A global mean cannot distinguish uniform underexposure
from a well-exposed finger against a very dark background. In production,
this metric should be computed only within the segmented ROI (see
`check_roi_completeness`) once available, rather than the full frame.

## 3. Glare Detection — Over-Saturation Ratio

**Idea:** Specular reflections off wet or oily skin (or a phone flash
reflecting directly back into the lens) produce clusters of pixels at or
near maximum sensor intensity (255), washing out ridge detail in those
regions.

**Algorithm:**
1. Convert to grayscale.
2. Count pixels where `intensity > 240`.
3. Divide by total pixel count to get `glare_fraction`.
4. Flag `has_glare` if `glare_fraction` exceeds the maximum tolerance
   (default `0.05`, i.e. 5% of the frame).

## 4. ROI Completeness — Otsu Thresholding + Area Ratio

**Idea:** Before ridge-level analysis is meaningful, the pipeline must
confirm the finger actually occupies a sufficient portion of the frame.
Otsu's method automatically selects a binarization threshold that best
separates a bimodal grayscale histogram (finger vs. background) without
requiring a hand-tuned constant.

**Algorithm:**
1. Convert to grayscale and apply a `5x5` Gaussian blur to suppress noise
   that would otherwise fragment the binary mask.
2. Apply `cv2.threshold` with `THRESH_BINARY + THRESH_OTSU` to obtain a
   binary foreground/background mask.
3. Because Otsu does not know which class is the "finger" a priori, the
   implementation takes whichever binary class occupies the *minority* of
   the frame — under a well-composed contactless capture guide, the finger
   is expected to be centered but not dominate the entire frame area.
4. Compute `roi_fraction = foreground_pixels / total_pixels`.
5. Flag `roi_complete = roi_fraction >= min_roi_ratio` (default `0.15`).

**Production upgrade path:** A learned segmentation model (e.g. a small
U-Net) or HSV skin-color gating would be materially more robust than pure
intensity thresholding, particularly under variable backgrounds — see
`report.md`, Question 2.

## 5. Ridge Clarity — Gabor Filter Response Variance

**Idea:** Fingerprint ridges are a locally periodic, orientation-specific
texture. A 2D Gabor filter is a sinusoidal plane wave modulated by a
Gaussian envelope — i.e. an orientation- and frequency-selective bandpass
filter — making it the natural tool for measuring ridge-like structure
strength, which is why Gabor filters are foundational to classical
fingerprint enhancement (e.g. Hong et al., 1998).

**Algorithm:**
1. Convert to grayscale.
2. Construct four Gabor kernels at `0°, 45°, 90°, 135°` orientations
   (`sigma=5.0`, `lambda=10.0`, `gamma=0.5`), covering the dominant ridge
   orientations regardless of finger rotation.
3. Convolve the grayscale image with each kernel via `cv2.filter2D`.
4. Compute the variance of each filtered response, then average across
   the four orientations to obtain a single `ridge_score`.
5. Flag `ridges_clear = ridge_score >= threshold` (default `15.0`).

**Why average across orientations rather than take the maximum?**
Averaging penalizes captures where ridge structure is only strong in one
direction (e.g. partially blurred or partially glared regions), giving a
more conservative and representative clarity estimate than taking the
best-case single-orientation response.

## 6. Composite Scoring & Gating

Each raw metric is independently normalized onto `[0, 1]` (see
`docs/formulas.md` for the exact formulas), then combined via a weighted
sum and scaled to `[0, 100]`:

```
composite = 100 * (w_blur*N_blur + w_bright*N_bright + w_glare*N_glare
                    + w_roi*N_roi + w_ridge*N_ridge)
```

A capture **passes** the gate only if **both**:
1. `composite >= pass_score` (default `60.0`), **and**
2. None of the five hard-failure boolean flags are set
   (`is_blurry`, `too_dark`, `too_bright`, `has_glare`,
   `not roi_complete`, `not ridges_clear`).

This dual condition prevents a capture with one severely failing metric
(e.g. extreme glare) from "passing on average" simply because its other
four metrics scored near-perfectly — a single catastrophic quality defect
should always block downstream processing regardless of composite score.
