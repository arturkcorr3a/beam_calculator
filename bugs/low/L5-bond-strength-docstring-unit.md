# L5 — `design_bond_strength` docstring unit says "kN/cm" (should be kN/cm²)

**Severity:** LOW
**Location:** `src/calculators/anchorage_calculator.py:77`

## Diagnosis
Bond strength is a stress → kN/cm², not force-per-length.

## Impact
Documentation only.

## Suggested fix
Correct the docstring unit.
