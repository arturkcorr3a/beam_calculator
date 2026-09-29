# C2 — Slab-edge support resolution divides by zero on an edge with no spans

**Severity:** CRITICAL
**Location:** `src/pavement_elements/slab_edge.py:83–84`

## Diagnosis
`total_length = supported_length + fixed_length`; then `fixed_length / total_length`.
If `self.spans` is empty, `total_length == 0` → `ZeroDivisionError`. Nothing
guarantees an edge always has spans.

## Impact
Crash on degenerate / mis-resolved geometry.

## Suggested fix
`if total_length == 0: return` (or skip) before the ratio.
