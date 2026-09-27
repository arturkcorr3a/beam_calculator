# M10 — `RebarCalculator.calculate()` convergence loop has no iteration cap

**Severity:** MEDIUM
**Location:** `src/calculators/rebar_calculator.py:98–116`

## Diagnosis
`while abs(current_d - self.d) > 0.01` with `cleanup()` clearing the `d` cache each pass.
If the chosen bar layout flips between two configs, `d` can oscillate and the loop never
terminates. Feeds into the risk in [M11](M11-actual-y-negative-sqrt.md).

## Impact
Potential infinite loop on pathological sections.

## Suggested fix
Add a max-iteration cap; on non-convergence raise or take the last value.
