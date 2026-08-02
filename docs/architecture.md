# System Architecture

## 1. High-Level Data Flow

```
                 ┌──────────────────────┐
                 │   Phone Camera Image  │
                 │   (.jpg / .png file)  │
                 └──────────┬────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   image_utils.py      │
                 │   load_image()        │
                 │   -> BGR np.ndarray   │
                 └──────────┬────────────┘
                            │
                            ▼
      ┌─────────────────────────────────────────────┐
      │                 metrics.py                    │
      │  check_blur()        check_brightness()        │
      │  check_glare()       check_roi_completeness()   │
      │  check_ridge_clarity()                          │
      └──────────────────────┬────────────────────────┘
                              │  5 raw metric dicts
                              ▼
                 ┌──────────────────────┐
                 │     scoring.py         │
                 │ compute_composite_score│
                 │  -> normalize [0,1]    │
                 │  -> weighted sum *100  │
                 └──────────┬────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    guidance.py         │
                 │ resolve_guidance()     │
                 │  -> single message     │
                 └──────────┬────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  scoring.quality_gate()│
                 │  -> passed (bool)      │
                 │  -> composite_score    │
                 │  -> per-metric results │
                 │  -> guidance string    │
                 └──────────┬────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌────────────────────┐     ┌────────────────────────┐
   │  quality_app.py      │     │  test_quality.py         │
   │  (Streamlit UI)       │     │  (batch CLI evaluation)   │
   └────────────────────┘     └────────────────────────┘
```

## 2. Module Responsibilities

| Module | Responsibility | Depends on |
|---|---|---|
| `utils/image_utils.py` | Image loading, decoding, validation, grayscale conversion, safe arithmetic helpers. Contains **no** business logic or thresholds. | `cv2`, `numpy` |
| `utils/metrics.py` | Implements the five independent quality metrics. Each function accepts a BGR image and returns a plain dict of raw + boolean results. Pure functions — no shared state. | `image_utils` |
| `utils/scoring.py` | Normalizes each raw metric into `[0, 1]`, computes the weighted composite score, applies hard-failure gating, and orchestrates the full pipeline in `quality_gate()`. | `metrics`, `guidance`, `image_utils` |
| `utils/guidance.py` | Maps the boolean failure flags produced by `metrics.py` onto a single prioritized, human-readable message. | none (pure logic) |
| `quality_assessment.py` | Thin public facade re-exporting the `utils` package API at the project root, matching the assignment's expected import surface (`from quality_assessment import quality_gate`). | `utils` |
| `quality_app.py` | Streamlit dashboard: sidebar threshold/weight controls, image upload, metric cards, guidance banner, optional batch preview. | `quality_assessment`, `streamlit`, `cv2` |
| `test_quality.py` | CLI batch-evaluation harness: walks `test_dataset/`, calls `quality_gate()` per image, aggregates timing/accuracy, exports `test_results.csv`. | `quality_assessment`, `pandas` |
| `generate_dummy_dataset.py` | Procedurally synthesizes fingerprint-like ridge images across all four test categories so the project runs without physical hardware. | `cv2`, `numpy` |

## 3. Design Principles

1. **Separation of concerns.** Metric computation (`metrics.py`), score
   aggregation (`scoring.py`), and user-facing messaging (`guidance.py`)
   are independently testable modules with no circular dependencies.
2. **Pure functions.** Every metric function is a pure function of its
   input image and threshold arguments — no hidden global state — which
   makes them trivial to unit test and safe to call concurrently.
3. **Single source of truth for defaults.** `DEFAULT_THRESHOLDS` and
   `DEFAULT_WEIGHTS` live once in `scoring.py` and are imported everywhere
   else (CLI, UI, facade) rather than being redefined per-caller.
4. **Fail loud, fail early.** `image_utils.load_image()` raises a typed
   `ImageLoadError` (converted to `ValueError` at the `quality_gate()`
   boundary) rather than silently returning `None`, so callers cannot
   accidentally operate on a corrupt/missing image.
5. **UI/logic decoupling.** `quality_app.py` never computes a metric or
   threshold decision itself — it only collects slider values and passes
   them into `quality_gate()`, guaranteeing that the CLI batch tool and the
   dashboard can never disagree on scoring logic.
