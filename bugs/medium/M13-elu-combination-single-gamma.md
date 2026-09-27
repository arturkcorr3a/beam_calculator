# M13 — `normal_elu_combination` applies a single γ=1.4 to (permanent+variable)

**Severity:** MEDIUM
**Location:** `src/loading/forces.py:91–104`

## Diagnosis
Returns `1.4 * (permanent + variable)`, ignoring ψ₀ combination factors for multiple
variable actions (TODO on line 90 acknowledges this). Fine for a single variable action;
incorrect when several variable actions should combine with ψ₀.

## Impact
Un/over-conservative with multiple variable actions.

## Suggested fix
Implement γg/γq + ψ₀, or rename to reflect the single-action simplification.
