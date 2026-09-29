# M7 — `_pick_best_option` raises bare `IndexError` on infeasible shear design

**Severity:** MEDIUM
**Location:** `src/reinforcement/stirrups.py:69–81` (called from line 65)

## Diagnosis
If the spacing loop (59–63) produces no valid option (e.g. `max_spacing <= MIN_SPACING`,
or no diameter meets the ratio), `options` is empty and `option_ratios[0]` raises an
uninformative `IndexError`.

## Impact
Cryptic crash instead of a meaningful "infeasible" error.

## Suggested fix
Guard empty `options`, raise a descriptive `ValueError`.
