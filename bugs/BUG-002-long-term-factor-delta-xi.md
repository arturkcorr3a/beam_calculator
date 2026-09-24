# BUG-002 — Long-term deflection factor uses `ξ(∞)` instead of `Δξ`

| Field | Value |
|---|---|
| **ID** | BUG-002 |
| **Severity** | 🔴 Critical |
| **Status** | Open |
| **File** | `src/checkers/deformation_checker.py` |
| **Lines** | 147–152 |
| **Method** | `DeformationChecker.long_term_deflection` |

## Description

The creep multiplier $\alpha_f$ is computed using the full long-term time coefficient
$\xi(\infty) = 2.0$ instead of the **incremental** value
$\Delta\xi = \xi(\infty) - \xi(t_0)$, as required by ABNT NBR 6118.
This overstates the long-term deflection by roughly 21%.

## Root Cause

ABNT NBR 6118:2026 — Section 17.3.2.1.2 defines the additional deflection factor as:

$$\alpha_f = \frac{\Delta\xi}{1 + 50\rho'}, \quad \Delta\xi = \xi(t) - \xi(t_0)$$

where $t_0$ is the age of the concrete when shores are removed.

For the common construction scenario (shores removed at $t_0 = 14$ days,
final long-term state $t \to \infty$):

$$\xi(\infty) = 2.0, \quad \xi(t_0 = 14\ \text{days}) \approx 0.53$$

$$\Delta\xi = 2.0 - 0.53 = 1.47 \implies \alpha_f = 1.47$$

The current code skips the subtraction of $\xi(t_0)$ entirely:

```python
# deformation_checker.py, lines 147–152
time_coefficient = 2  # ξ(∞), NOT Δξ
fluency_factor = time_coefficient / (1 + 50 * rho)
long_term_deflection = (1 + fluency_factor) * self.immediate_deflection
```

This computes a total multiplier of `1 + 2.0 = 3.0` instead of the correct
`1 + 1.47 = 2.47` — a **21% overestimate** of the final deflection.

## Numerical Impact (example from the guide)

| Quantity | Code result | Correct result |
|---|---|---|
| $\alpha_f$ | `2.0` | `1.47` |
| Total multiplier $(1 + \alpha_f)$ | `3.0` | `2.47` |
| $a_{total}$ (from guide example) | `5.37 mm` | `4.42 mm` |

## Fix

```python
# deformation_checker.py — long_term_deflection property
xi_inf = 2.0   # ξ(∞), per ABNT NBR 6118 – 17.3.2.1.2
xi_t0 = 0.53   # ξ(t₀ = 14 days) — shores removed 14 days after casting
# PAPER — formula for ξ(t): 0.68 · 0.996^t · t^0.32 (t in months)
delta_xi = xi_inf - xi_t0
fluency_factor = delta_xi / (1 + 50 * rho)
long_term_deflection = (1 + fluency_factor) * self.immediate_deflection
```

> **Note:** `t_0` (age at shore removal) should ideally be a configurable parameter
> from `AppConfig` rather than a hard-coded constant, since it affects `ξ(t_0)`.

## Reference

- ABNT NBR 6118:2026 — Section 17.3.2.1.2 (Long-term additional deflection)
- Carvalho & Figueiredo Filho — Section 7.3.7.2.1 (p. 332–333)

