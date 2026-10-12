# M15 — `resolve_support_condition` uses a hardcoded `0.8`, not the named constant

**Severity:** MEDIUM
**Location:** `src/pavement_elements/slab_edge.py:97` (constant `FIXED_RATIO_THRESHOLD` at line 19)

## Diagnosis
`if fixed_length / total_length > 0.8` should use the module constant
`FIXED_RATIO_THRESHOLD`. The constant exists but is unused, so tuning it silently has
no effect.

## Impact
Maintainability; silent inconsistency between constant and behaviour.

## Suggested fix
Use `FIXED_RATIO_THRESHOLD`.
