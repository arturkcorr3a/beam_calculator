# L3 — Copy-pasted "Beam" in `Slab._validate_pillars_exist`

**Severity:** LOW
**Status:** Fixed — the message now says "Slab" (docs/UI_SPEC.md §5.3, S5).
**Location:** `src/pavement_elements/slab.py:329–335`

## Diagnosis
Error message says `f"Beam '{self.id}': …"` inside a `Slab` method (copied from
`ContinuousBeam`).

## Impact
Misleading diagnostics only.

## Suggested fix
Change "Beam" to "Slab".
