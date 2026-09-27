# L8 — `get_layer_relative_centroid_with_weight` docstring says "mm" (computes cm)

**Severity:** LOW
**Location:** `src/reinforcement/reinforcement.py:246`

## Diagnosis
Centroid is computed in cm (`bar_diameter_cm`, areas in cm²) and consumed as cm; the
docstring says "mm".

## Impact
Documentation only; misleading.

## Suggested fix
Change "mm" to "cm".
