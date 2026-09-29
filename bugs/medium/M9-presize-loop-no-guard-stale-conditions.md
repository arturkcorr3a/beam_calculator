# M9 — Slab pre-sizing loop: no convergence guard, and stale support conditions

**Severity:** MEDIUM
**Location:** `src/pavement_elements/pavement.py:102–117` (with `slab.py:160–162`)

## Diagnosis
The `while False in stable or None in stable` fixed-point loop has no max-iteration cap.
Support conditions are resolved once at pre_size time and not re-resolved between passes,
so a neighbour's thickness change can leave "stable" reporting on stale conditions, and
an oscillating resize could spin.

## Impact
Potential non-convergence / stale support conditions in multi-slab pavements.

## Suggested fix
Add a max-pass guard; re-resolve support conditions each pass.
