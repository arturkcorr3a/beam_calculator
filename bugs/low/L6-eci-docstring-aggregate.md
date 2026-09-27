# L6 — `eci` docstring hardcodes "granite and gneiss aggregate"

**Severity:** LOW
**Location:** `src/properties/concrete.py:64,77`

## Diagnosis
αE is actually read from config (`alpha_e`, lines 44–59) and covers all aggregate types;
the docstring states an assumption the code doesn't make.

## Impact
Documentation only; misleading.

## Suggested fix
Remove/relax the aggregate claim in the docstring.
