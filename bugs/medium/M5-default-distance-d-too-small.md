# M5 — `DEFAULT_DISTANCE_FOR_D_CALCULATION` too small vs its own comment

**Severity:** MEDIUM
**Location:** `src/reinforcement/reinforcement.py:18`

## Diagnosis
Value `1.0` cm, comment "default 1 layer with 20 mm bars." A real single layer sits at
≈ cover + stirrup + φ/2 ≈ 4 cm from the edge, not 1 cm.

## Impact
First-iteration `d = h − d'` is overestimated → unconservative initial bending design
(refined later by the convergence loop, so effect is bounded).

## Suggested fix
Use ≈4 cm, or compute from cover + stirrup + half bar.
