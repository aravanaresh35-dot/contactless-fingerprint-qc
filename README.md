# 📱 Contactless Fingerprint Quality Assessment & Scoring Pipeline

An automated **Image Quality Control (QC) pipeline** for contactless mobile
fingerprint authentication systems. It filters out defective phone-camera
captures — blur, poor lighting, glare, incomplete framing, low ridge
contrast — *before* they reach downstream segmentation, minutiae
extraction, or matching models, and gives users real-time, actionable
feedback to fix their capture.

---

## 1. Project Overview

Contactless biometrics move fingerprint capture from dedicated optical/
capacitive scanners to ordinary phone cameras. That convenience comes at a
cost: captures vary wildly in blur, exposure, glare, distance, and
orientation, and low-quality images cause silent downstream failures in
deep-learning matching pipelines.

This project implements a **sub-300ms quality gate** that:

1. Scores five fundamental image-quality metrics (blur, brightness, glare,
   ROI completeness, ridge clarity).
2. Combines them into a single normalized **composite score (0–100)**.
3. Applies hard pass/fail gating logic.
4. Returns a single, prioritized, human-readable **guidance message**
   telling the user exactly what to fix.
5. Exposes everything through an interactive **Streamlit dashboard** with
   live threshold tuning.

## 2. Features

- ✅ **Blur detection** — Laplacian variance
- ✅ **Brightness assessment** — grayscale mean intensity (under/over exposure)
- ✅ **Glare detection** — over-saturation pixel ratio
- ✅ **ROI completeness** — Otsu thresholding + contour/foreground area ratio
- ✅ **Ridge clarity** — multi-orientation Gabor filter response variance
- ✅ **Composite scoring** — configurable weighted normalization (0–100)
- ✅ **Master quality gate** — single pass/fail decision with failure hierarchy
- ✅ **Prioritized guidance messages** — one clear instruction at a time
- ✅ **Dynamic threshold tuning** — live sliders, no code changes required
- ✅ **Modern Streamlit dashboard** — score pill, metric cards, guidance banner
- ✅ **Batch testing framework** — evaluates an entire labeled dataset
- ✅ **CSV export** — machine-readable results for regression tracking
- ✅ **Synthetic dataset generator** — runs out-of-the-box with no hardware
- ✅ **< 300 ms total pipeline latency**, comfortably within the performance budget

## 3. Folder Structure

```
contactless-fingerprint-qc/
│
├── quality_assessment.py     # Public facade: metric functions + quality_gate()
├── quality_app.py            # Streamlit UI dashboard with dynamic sliders
├── test_quality.py           # Batch testing script over test_dataset/
├── generate_dummy_dataset.py # Synthetic fingerprint-like dataset generator
├── requirements.txt          # Python dependency list
├── README.md                 # This file
├── .gitignore
├── LICENSE
├── report.md                 # Written answers to conceptual report questions
├── report.pdf                # (markdown-sourced) PDF version of the report
├── test_results.csv          # Latest batch evaluation output
├── sample_output.md          # Example quality_gate() output walkthrough
│
├── utils/                    # Modular core implementation
│   ├── __init__.py
│   ├── image_utils.py        # Image I/O helpers
│   ├── metrics.py             # The 5 core quality metric functions
│   ├── scoring.py             # Normalization, composite score, quality_gate()
│   └── guidance.py            # Prioritized guidance message resolution
│
├── test_dataset/              # 20 test images (5 per condition)
│   ├── good/
│   ├── blurry/
│   ├── dark/
│   └── glare/
│
├── screenshots/               # Dashboard screenshots for documentation
│
└── docs/
    ├── architecture.md        # System architecture & module responsibilities
    ├── algorithm.md           # Algorithmic explanation of each metric
    └── formulas.md            # Full mathematical formulation
```

## 4. Installation

### 4.1 Prerequisites

- Python 3.9 or higher
- pip

### 4.2 Setup

```bash
git clone https://github.com/<your-username>/contactless-fingerprint-qc.git
cd contactless-fingerprint-qc

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 5. Requirements

| Package | Purpose |
|---|---|
| `opencv-python` | Image processing, edge detection, filtering, histogram operations |
| `numpy` | Array manipulation and fast numerical operations |
| `streamlit` | Web dashboard for live feedback and threshold tuning |
| `pandas` | Tabular formatting for batch testing results |
| `pillow` | Image file handling |
| `matplotlib` | Optional visualization support |

## 6. How to Run

### 6.1 Generate the test dataset (only needed once, no hardware required)

```bash
python generate_dummy_dataset.py
```

This procedurally synthesizes 20 fingerprint-like images (5 good, 5 blurry,
5 dark, 5 glare) into `test_dataset/`. Replace these with real smartphone
captures at any time — the pipeline works identically on either.

### 6.2 Run the Streamlit dashboard

```bash
streamlit run quality_app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`) in
your browser. Upload an image, adjust thresholds in the sidebar, and watch
the composite score, pass/fail status, and guidance message update live.

### 6.3 Run batch evaluation from the command line

```bash
python test_quality.py
```

This evaluates every image in `test_dataset/`, prints a summary table, and
writes `test_results.csv`.

### 6.4 Programmatic usage

```python
from quality_assessment import quality_gate

result = quality_gate("path/to/capture.jpg")
print(result["passed"], result["composite_score"], result["guidance"])
```

## 7. Screenshots

> Screenshots of the running dashboard belong in `screenshots/`. Suggested
> captures to include once you run the app locally:
>
> - `screenshots/dashboard_pass.png` — a PASSED capture with green score pill
> - `screenshots/dashboard_fail.png` — a REJECTED capture with red score pill
>   and an active guidance banner
> - `screenshots/sidebar_thresholds.png` — the threshold-tuning sidebar
> - `screenshots/batch_results.png` — the batch-evaluation summary table

## 8. Performance Budget

| Stage | Target | Method |
|---|---|---|
| Blur check | < 10 ms | Laplacian variance |
| Brightness check | < 5 ms | Grayscale mean intensity |
| Glare check | < 10 ms | Over-saturation ratio |
| ROI completeness | < 100 ms | Otsu thresholding + area ratio |
| Ridge clarity | < 150 ms | Gabor filter response variance |
| **Total pipeline** | **< 300 ms** | Combined gate execution |

Measured latency for the bundled synthetic dataset is reported at the end
of every `test_quality.py` run and inside the Streamlit dashboard for each
uploaded image.

## 9. Future Improvements

- **Perspective / pitch-yaw distortion check** — detect and reject
  severely angled captures that warp ridge spacing.
- **Multi-finger occlusion detection** — flag frames where adjacent
  fingers intrude on the ROI.
- **Distance/scale boundary check** — estimate effective capture DPI and
  reject captures that are too far (low resolution) or too close
  (out-of-focus range).
- **On-device model export** — port the metric functions to a
  TensorFlow Lite / Core ML pipeline for real-time in-camera feedback
  before the shutter is pressed.
- **Adaptive thresholding for worn ridges** — auto-calibrate ridge
  clarity thresholds per-user using CLAHE-enhanced enrollment samples
  (see `report.md`, Question 5).
- **Multi-frame fusion** — capture a short burst and fuse frames into a
  single higher-quality composite before scoring.
- **NFIQ2-informed calibration** — validate composite score thresholds
  against a labeled dataset scored with NFIQ2-equivalent tooling adapted
  for contactless imagery.

## 10. License

Released under the [MIT License](LICENSE).
