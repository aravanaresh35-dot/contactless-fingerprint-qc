# Sample `quality_gate()` Output

This document walks through two real outputs produced by running the
pipeline against images in the bundled `test_dataset/` (generated via
`python generate_dummy_dataset.py` and evaluated via
`python test_quality.py`). Use it as a quick reference for the exact shape
of the dictionary returned by `quality_gate()`.

---

## Example 1 — A PASSING capture (`test_dataset/good/good_01.jpg`)

```python
from quality_assessment import quality_gate

result = quality_gate("test_dataset/good/good_01.jpg")
```

```json
{
  "passed": true,
  "composite_score": 97.6,
  "normalized_scores": {
    "blur": 1.0,
    "brightness": 0.8542,
    "glare": 1.0,
    "roi": 0.9886,
    "ridge": 1.0
  },
  "blur": {
    "blur_score": 507.71,
    "is_blurry": false
  },
  "brightness": {
    "brightness": 146.66,
    "too_dark": false,
    "too_bright": false
  },
  "glare": {
    "glare_fraction": 0.0,
    "has_glare": false
  },
  "roi": {
    "roi_fraction": 0.346,
    "roi_complete": true
  },
  "ridge": {
    "ridge_score": 1359.29,
    "ridges_clear": true
  },
  "guidance": "Good capture — ready for processing.",
  "thresholds_used": {
    "blur_threshold": 10.0,
    "blur_norm_cap": 50.0,
    "brightness_min": 50.0,
    "brightness_max": 210.0,
    "brightness_ideal": 128.0,
    "glare_max_ratio": 0.05,
    "roi_min_ratio": 0.15,
    "roi_norm_cap": 0.35,
    "ridge_threshold": 15.0,
    "ridge_norm_cap": 30.0,
    "pass_score": 60.0
  },
  "weights_used": {
    "blur": 0.25,
    "brightness": 0.15,
    "glare": 0.15,
    "roi": 0.2,
    "ridge": 0.25
  }
}
```

All five sub-checks pass, the composite score (97.6) comfortably clears
the pass threshold (60.0), and the guidance banner confirms the capture is
ready for downstream processing.

---

## Example 2 — A REJECTED capture (`test_dataset/dark/dark_01.jpg`)

```python
result = quality_gate("test_dataset/dark/dark_01.jpg")
```

```json
{
  "passed": false,
  "composite_score": 69.4,
  "normalized_scores": {
    "blur": 0.2448,
    "brightness": 0.2277,
    "glare": 1.0,
    "roi": 0.9957,
    "ridge": 1.0
  },
  "blur": {
    "blur_score": 12.24,
    "is_blurry": false
  },
  "brightness": {
    "brightness": 29.14,
    "too_dark": true,
    "too_bright": false
  },
  "glare": {
    "glare_fraction": 0.0,
    "has_glare": false
  },
  "roi": {
    "roi_fraction": 0.3485,
    "roi_complete": true
  },
  "ridge": {
    "ridge_score": 56.05,
    "ridges_clear": true
  },
  "guidance": "Lighting is too dark. Turn on your flash or move to a lit area.",
  "thresholds_used": { "...": "same as above" },
  "weights_used": { "...": "same as above" }
}
```

This is the key behavior of the **hard-failure gate**: even though the
composite score (69.4) is *above* the 60.0 pass threshold, the capture is
still rejected because `brightness.too_dark` is `true`. A single
catastrophic quality defect always blocks the gate, regardless of how well
the other four metrics score — see `docs/algorithm.md` §6 for the full
reasoning.

---

## Batch Summary (from `test_quality.py`)

Running the full 20-image synthetic dataset produces a console summary
similar to:

```
================ QUALITY CONTROL BATCH EVALUATION ================

File           Expected Category  Passed  Composite Score  ...  Guidance
good_01.jpg    good               True    97.6                 Good capture — ready for processing.
blur_01.jpg    blurry             False   77.5                 Image is too blurry. Hold your camera steady and re-focus.
dark_01.jpg    dark               False   69.4                 Lighting is too dark. Turn on your flash or move to a lit area.
glare_01.jpg   glare              False   57.2                 Image is too blurry. Hold your camera steady and re-focus.
...

Classification accuracy vs. expected category label: 95.0%
Average pipeline latency: 228.31 ms (budget: 300 ms)

Results written to 'test_results.csv'.
```

The full machine-readable results are written to `test_results.csv` at the
project root after every run.
