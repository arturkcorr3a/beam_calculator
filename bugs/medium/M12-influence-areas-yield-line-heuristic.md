# M12 — `resolve_influence_areas` yield-line pattern picked by a single-coordinate test

**Severity:** MEDIUM
**Location:** `src/pavement_elements/slab.py:284`

## Diagnosis
The vertical-vs-horizontal yield-line topology is chosen by `p_bottom.y < p_left.y`. For
near-square slabs with mixed supports this heuristic can select the wrong topology and
mis-distribute tributary load to the beams. No reference cited.

## Impact
Wrong tributary load split → wrong beam loads.

## Suggested fix
Derive the pattern from lx/ly and edge conditions explicitly; add tests asserting
influence areas sum to the slab area.
