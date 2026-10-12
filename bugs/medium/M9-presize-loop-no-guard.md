# M9 — Slab pre-sizing fixed-point loop has no convergence guard

**Severity:** MEDIUM
**Location:** `src/pavement_elements/pavement.py:99–118` (`pre_size_slabs`)

## Diagnosis
The `while False in stable or None in stable` fixed-point loop has no maximum-pass cap.
Each slab's thickness depends on its neighbours' thicknesses (through the support
conditions). An oscillating resize between adjacent slabs would therefore spin
forever.

(The earlier "stale support conditions" half of this report is fixed:
`Slab.pre_size` now re-resolves support conditions at every thickness tried —
`slab.py:259,283`.)

## Impact
Potential infinite loop in multi-slab pavements.

## Suggested fix
Add a max-pass guard (e.g. a config or module constant) and raise a descriptive
`ValueError` that lists the slabs still changing when the cap is hit.
