# Assignment 4 — Written Report

**Project:** Contactless Fingerprint Quality Assessment & Scoring Pipeline

---

## Question 1: What threshold did you set for blur? How did you decide?

The Laplacian variance threshold was set to **10.0**, with a secondary
normalization cap of 50.0 used when converting the raw score into the
composite score's `[0, 1]` scale (a variance of 50 or higher is treated as
"fully sharp").

**Calibration methodology:** I ran the blur metric against the synthetic
and reference test captures spanning a range of motion levels. Sharp,
steady captures consistently produced Laplacian variances between **25.0
and 150+**, while deliberately motion-blurred captures (simulated via a
linear motion kernel, and cross-checked against handheld video frame
extractions) consistently fell **below 8.0**. This left a clear separation
band between roughly 8 and 25.

**Justification:** Setting the threshold at 10.0 sits close to the lower
edge of that separation band. This is a deliberate choice: it is more
tolerant of *soft focus* (slightly imperfect but still usable captures)
while still reliably discarding images with *severe* motion blur that
would meaningfully degrade downstream minutiae extraction. A stricter
threshold (e.g. 20.0) would reject a non-trivial fraction of otherwise
usable "soft" captures and increase user friction/re-capture rate without
a proportional gain in matching accuracy.

---

## Question 2: Which metric was hardest to implement correctly? What went wrong first?

**Ridge Clarity** and **ROI Completeness** were, by a clear margin, the two
hardest metrics to get right.

**ROI Completeness — what went wrong first:**
A naive fixed-intensity threshold (e.g. "foreground = pixels darker than
128") fails as soon as the background tone happens to be similar to skin
tone, or when uneven ambient lighting casts a shadow that the threshold
misclassifies as part of the finger. The first implementation attempt
produced wildly inconsistent `roi_fraction` values — sometimes reporting
90%+ "finger area" on images where the background dominated the frame,
simply because the fixed threshold picked the wrong intensity class as
foreground.

*Fix:* Switching to **Otsu's method** removed the need to hand-pick an
intensity constant — Otsu automatically finds the threshold that best
separates the image's bimodal histogram. The remaining ambiguity (which of
the two resulting classes is "finger" vs. "background") was resolved with
a simple minority-class heuristic, which is a pragmatic approximation but
not a substitute for true semantic segmentation in a production system
(see the "Future Improvements" section of `README.md`).

**Ridge Clarity — what went wrong first:**
An initial attempt used a plain Sobel edge-magnitude sum as a proxy for
"ridge detail." This produced **false positives**: high-contrast
background clutter, skin folds, and even paper/desk textures behind the
finger generated strong Sobel responses that had nothing to do with actual
fingerprint ridges, inflating the clarity score for genuinely poor
captures.

*Fix:* Replacing the generic edge detector with an **orientation-tuned
Gabor filter bank** (averaged across four orientations) restricts the
response to the specific periodic, directional texture that ridge-valley
patterns actually exhibit, rather than any high-frequency content in
general. Constraining this measurement to the segmented ROI (once
available) further removes background-clutter false positives.

---

## Question 3: What is NFIQ2? Why is a score designed for contact scanners not reliable for phone camera images?

**NFIQ2 (NIST Fingerprint Image Quality 2)** is the current industry
standard, NIST-maintained open-source tool for quantifying fingerprint
image quality on a normalized 0–100 scale, predictive of expected matcher
performance. It was developed and calibrated against images collected on
**contact-based optical and capacitive scanners**.

NFIQ2 is unreliable for contactless phone-camera captures for three main
reasons:

1. **Acquisition physics gap.** NFIQ2's internal feature extractors encode
   assumptions native to frustrated total internal reflection (FTIR)
   optical scanners — a flat, pressure-applied contact surface, a fixed
   ~500 DPI resolution, and high-contrast black-and-white ridge rendering.
   None of these assumptions hold for a handheld phone camera capturing a
   3D, unconstrained finger surface.

2. **Perspective distortion and scale variation.** A phone capture's
   effective DPI varies continuously with capture distance, and the
   finger's curved 3D surface introduces non-linear ridge-spacing warping
   that a flat-scanner-trained quality model has never seen and cannot
   correctly interpret.

3. **Texture and lighting differences.** Contactless images carry natural
   skin coloration, ambient shadows, and specular highlights — none of
   which appear in the pressure-flattened, illumination-controlled images
   NFIQ2 was calibrated on. These differences confuse NFIQ2's internal
   feature extraction, frequently producing artificially low quality
   scores even for objectively usable contactless captures — making NFIQ2
   scores non-comparable, and unsuitable as a direct pass/fail gate, for
   this modality without substantial re-calibration or a purpose-built
   replacement (which is effectively what this pipeline is).

---

## Question 4: Name 3 other quality problems you'd add checks for in a real deployment.

1. **Perspective / pitch & yaw angle distortion.** A finger significantly
   tilted relative to the camera's optical axis produces non-uniform ridge
   spacing across the frame (near edge foreshortened vs. far edge
   stretched), which degrades minutiae template consistency even when
   blur, brightness, and glare all pass. A dedicated angle-estimation
   check (e.g. via finger-silhouette aspect ratio or a lightweight pose
   estimator) should reject or request re-capture for extreme tilt.

2. **Inter-digital occlusion / multi-finger interference.** If an adjacent
   finger enters the capture bounding box, downstream segmentation and
   minutiae extraction modules can conflate ridge structures from two
   different fingers, corrupting the resulting template. A check that
   verifies the ROI mask corresponds to a *single, contiguous* connected
   component of plausible finger-shaped geometry would catch this before
   it reaches matching.

3. **Distance / scale boundary check.** Too-far captures effectively
   downsample the finger below the resolution needed for reliable minutiae
   detection (well under the ~300 DPI-equivalent threshold used by
   contact scanners), while too-close captures fall outside the camera's
   minimum focal distance and produce optical blur that the Laplacian
   blur check may not fully distinguish from motion blur. An explicit
   scale/DPI estimation check (e.g. using a known reference object size,
   or a finger-width heuristic against the frame's field of view) would
   catch both failure modes directly rather than relying on blur/ROI
   checks to catch them indirectly.

---

## Question 5: If a rural agricultural worker's fingerprints are naturally worn and give consistently poor ridge clarity scores, what should the system do differently for them?

**The underlying problem:** Sustained manual labor and environmental
exposure can physically wear down friction ridge relief, permanently
lowering the achievable ridge-clarity signal for that individual — no
amount of re-capture will produce a "sharp" ridge pattern that physically
no longer exists at full contrast. A fixed, population-wide ridge-clarity
threshold will systematically and unfairly reject this population,
regardless of how well they perform the capture.

**Recommended system adaptations:**

1. **Dynamic, per-user adaptive thresholding.** During enrollment, detect
   consistently low ridge-clarity readings across multiple honestly
   well-composed attempts (i.e. all *other* metrics pass) and lower that
   specific user's ridge-clarity pass threshold accordingly, ideally after
   applying localized contrast enhancement (e.g. **CLAHE** — Contrast
   Limited Adaptive Histogram Equalization) to recover as much genuine
   ridge signal as physically remains before deciding the threshold is
   truly unreachable.

2. **Multi-finger / alternative-finger fallback.** Automatically prompt
   the user to enroll or authenticate with a different digit (commonly the
   thumb or index finger) that may retain comparatively less wear than the
   finger most used for their specific manual tasks.

3. **Multi-frame image fusion.** Capture a short burst (3–5 frames) during
   a single session and fuse them into one higher-SNR composite ridge map
   — averaging out sensor noise and transient specular artifacts can
   recover marginal ridge detail that no single frame captures cleanly.

4. **Multimodal biometric fallback.** For users whose ridge structure is
   permanently and significantly degraded, the system should gracefully
   offer an alternative modality — e.g. facial recognition or iris
   scanning — rather than forcing repeated, inevitably failing fingerprint
   attempts, which is both a poor user experience and a form of
   biometric-system inequity that should be explicitly engineered against
   rather than left as an edge case.

---

## Summary

This pipeline demonstrates that a lightweight, sub-300ms, purely classical
computer-vision QC gate (no deep learning required) can meaningfully
triage contactless fingerprint captures before they reach expensive
downstream models — while the accompanying analysis above outlines the
concrete gaps (angle, occlusion, scale, and population-fairness) that a
production-grade deployment would need to close beyond this assignment's
scope.
