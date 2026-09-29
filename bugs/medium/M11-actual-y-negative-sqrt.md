# M11 — `actual_y` can hit `sqrt` of a negative number

**Severity:** MEDIUM
**Location:** `src/calculators/rebar_calculator.py:347–360`

## Diagnosis
`actual_y = d - sqrt(d**2 - 2*Md/(σ*bw))`. If `2·Md/(σ·bw) > d²` the radicand is
negative → `ValueError: math domain error`. Guarded in theory by `is_singly_reinforced`
bounding Md, but during the un-capped convergence loop
([M10](M10-rebar-convergence-no-cap.md)) a stale `d` can be evaluated with an
inconsistent moment.

## Impact
Possible math-domain crash during iteration.

## Suggested fix
Clamp the radicand ≥ 0 / guard before the `sqrt`.
