# Mathematical Formulation

## 1. Raw Metrics

### 1.1 Blur — Laplacian Variance

$$
\Delta I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}
\qquad\qquad
\text{blur\_score} = \mathrm{Var}\big(\Delta I_{gray}\big)
$$

Reject condition: $\text{blur\_score} < 10.0$

### 1.2 Brightness — Mean Intensity

$$
\mu = \frac{1}{N}\sum_{i=1}^{N} I_{gray}(i)
$$

Reject conditions: $\mu < 50$ (too dark) or $\mu > 210$ (too bright)

### 1.3 Glare — Over-Saturation Ratio

$$
\text{glare\_fraction} = \frac{\sum_i \mathbb{1}[I_{gray}(i) > 240]}{N_{total}}
$$

Reject condition: $\text{glare\_fraction} > 0.05$

### 1.4 ROI Completeness — Foreground Area Ratio

$$
\text{roi\_fraction} = \frac{\mathrm{Area}(M)}{\mathrm{Area}(I_{total})}
\quad\text{where } M = \text{Otsu}(I_{gray})
$$

Reject condition: $\text{roi\_fraction} < 0.15$

### 1.5 Ridge Clarity — Gabor Response Variance

$$
G_\theta(x,y) = \exp\!\left(-\frac{x'^2+\gamma^2 y'^2}{2\sigma^2}\right)
\cos\!\left(2\pi\frac{x'}{\lambda}+\psi\right)
$$

$$
x' = x\cos\theta + y\sin\theta, \qquad y' = -x\sin\theta + y\cos\theta
$$

$$
\text{ridge\_score} = \frac{1}{|\Theta|}\sum_{\theta \in \Theta}
\mathrm{Var}\big(I_{gray} * G_\theta\big) \Big/ 100.0,
\qquad \Theta = \{0°, 45°, 90°, 135°\}
$$

Reject condition: $\text{ridge\_score} < 15.0$

## 2. Normalization ($[0,1]$ range)

$$
N_{blur} = \min\!\left(1.0,\ \frac{\text{blur\_score}}{50.0}\right)
$$

$$
N_{bright} = \max\!\left(0.0,\ 1.0 - \frac{|\text{brightness} - 128|}{128}\right)
$$

$$
N_{glare} = \max\!\left(0.0,\ 1.0 - \frac{\text{glare\_fraction}}{0.05}\right)
$$

$$
N_{roi} = \min\!\left(1.0,\ \frac{\text{roi\_fraction}}{0.35}\right)
$$

$$
N_{ridge} = \min\!\left(1.0,\ \frac{\text{ridge\_score}}{30.0}\right)
$$

## 3. Composite Score

$$
\text{Composite Score} = 100 \times \sum_{i=1}^{5} w_i N_i
\qquad \sum_{i=1}^{5} w_i = 1.0
$$

Default weights:

| Metric | Weight |
|---|---|
| Blur | 0.25 |
| Brightness | 0.15 |
| Glare | 0.15 |
| ROI | 0.20 |
| Ridge | 0.25 |

## 4. Gate Decision

$$
\text{passed} = \big(\text{Composite Score} \ge 60.0\big)\ \wedge\
\big(\neg\,\text{is\_blurry} \wedge \neg\,\text{too\_dark} \wedge
\neg\,\text{too\_bright} \wedge \neg\,\text{has\_glare} \wedge\
\text{roi\_complete} \wedge \text{ridges\_clear}\big)
$$

Every symbol above corresponds directly to a returned field in
`quality_gate()`'s result dictionary, so this formulation can be verified
against `utils/scoring.py` line-by-line.
