# C3 — Quasi-permanent ELS factor ψ₂ is a no-op — always 0.30 regardless of usage

**Severity:** CRITICAL
**Location:** `src/loading/forces.py:60–64` (`get_almost_permanent_combination_reduction_factor`)

## Diagnosis
`if usage is None: return 0.3` else `return 0.30` — both branches return the same
value (there is a TODO on the line). `usage` is threaded all the way through the slab
load path (`slab_deformation_checker.design_load` passes `self.usage`) but has no
effect. Per NBR 6118 Table 11.2, ψ₂ varies by occupancy (residential 0.3, offices
0.4, assembly/libraries 0.6, …).

## Impact
Every ELS quasi-permanent combination uses ψ₂ = 0.3. **Unconservative** (underestimates
deflection & service moment) for all non-residential categories.

## Suggested fix
Implement the ψ₂ lookup by `building_category`/usage; remove the dead branch. Keep a
`# PAPER` tag if the exact table cross-reference still needs confirming.
