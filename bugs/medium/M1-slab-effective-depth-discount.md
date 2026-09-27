# M1 — Slab effective-depth discount uses 1.5× bar diameter

**Severity:** MEDIUM
**Location:** `src/checkers/slab_deformation_checker.py:27–33`

## Diagnosis
Returns `covering + 1.5 * rebar_discount_10_mm` (=covering+1.5 cm). The centroid
discount for a single layer should be `covering + φ/2` = covering+0.5 cm for a 10 mm
bar. The `1.5×` over-discounts by ~1 cm; unexplained.

## Impact
Systematically reduces `effective_depth` by ~1 cm for all slabs → biases deflection and
rebar-area results (conservative on deflection, but wrong).

## Suggested fix
`covering + 0.5 * bar_diameter_cm`, unless a documented two-layer convention justifies
1.5.
