# H4 — `calculate_moment_shift` divides by zero / negative when V_Sd ≤ V_c

**Severity:** HIGH
**Location:** `src/calculators/stirrup_calculator.py:125–141`

## Diagnosis
Denominator `2 * (self.design_shear_force - self.concrete_contribution)` (line 131).
When the applied shear does not exceed the concrete contribution (`V_Sd ≤ V_c`, i.e.
only minimum stirrups needed), this is zero or negative → `ZeroDivisionError` or a
garbage/exploding `a_l`. No guard.

Additionally, line 139 `moment_shift = max(al, 0.5*d)` is fully redundant — `al` is
already clamped to `≥ 0.5d` on line 138.

## Impact
Crash or nonsensical moment-shift on low-shear beams.

## Suggested fix
Guard the denominator; when `V_Sd ≤ V_c`, default `a_l` to the code minimum (`d` for
vertical stirrups per §9.4.2.3). Remove the redundant line 139.
