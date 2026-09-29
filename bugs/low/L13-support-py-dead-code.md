# L13 — Fully commented-out dead file `support.py`

**Severity:** LOW
**Location:** `src/structural_elements/support.py:1–17`

## Diagnosis
The entire `PillarSupport` stub is commented out (FIXME/TODO). The `Support` used in
`rectangular_beam.py:68` comes from `indeterminatebeam`, so this file is unused.

## Impact
Dead code / incomplete feature.

## Suggested fix
Remove or implement.
