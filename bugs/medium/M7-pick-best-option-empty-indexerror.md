# M7 — `_pick_best_option` raises bare `IndexError` on infeasible shear design

**Severity:** MEDIUM
**Location:** `src/reinforcement/stirrups.py:51–81` (`choose`, `_pick_best_option`)

## Diagnosis
If the spacing loop (lines 59–63) produces no valid option, `options` is empty and
`option_ratios[0]` (line 81) raises an uninformative `IndexError`. This happens when
`max_spacing <= MIN_SPACING`, or when no diameter within `[MIN_DIAMETER, max_diameter]`
meets the required ratio.

## Impact
Cryptic crash instead of a meaningful "infeasible" error.

## Suggested fix
Guard against an empty `options` list and raise a descriptive `ValueError` (required
ratio, max diameter, spacing range).
