# C4 — Slab self-weight is never transferred to the supporting beams

**Severity:** CRITICAL
**Location:** `src/pavement_elements/slab_edge.py:102–119` (`SlabEdge.unload_on_spans`),
`src/pavement_elements/slab.py:557–564` (`_resolve_permanent_load_without_own_weight`),
`src/checkers/slab_deformation_checker.py:57–73` (`own_weight_for_current_height`)

## Diagnosis
`Slab.permanent_load` is set during validation to the finishes only (top finish +
ceiling + infill — all zero by default), explicitly *without* own weight. The slab's own
weight (25 kN/m³ × h) is added only temporarily, inside the deflection checker's
`own_weight_for_current_height` context, and removed again afterwards. When the slab is
later unloaded onto its edge beams, `SlabEdge.unload_on_spans` uses
`self.slab.permanent_load`, so the beams receive the finishes and the variable load,
but **never the slab's self-weight**.

## Impact
Beam permanent loads are underestimated on every pavement. An 8 cm slab weighs
2.0 kN/m² — more than the 1.5 kN/m² live load of a residential bedroom — so beam
moments, shears, reinforcement and deflection checks are unconservative.

## Suggested fix
After slab pre-sizing (the thickness is final), include
`SuperficialLoads.get_concrete_element_own_weight(thickness / 100)` in the permanent load
used by `unload_on_spans` (e.g. a `Slab.total_permanent_load` property), and add a
regression test that a beam's span permanent load grows by own weight × influence area /
edge length.
