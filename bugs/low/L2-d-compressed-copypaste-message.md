# L2 — Copy-pasted error message in `d_compressed`

**Severity:** LOW
**Location:** `src/calculators/rebar_calculator.py:399`

## Diagnosis
In `d_compressed`, the `ValueError` reads "Tensioned reinforcement is marked chosen…" —
copied from `d()` (line 303). Should say "Compressed".

## Impact
Misleading diagnostics only.

## Suggested fix
Correct the message.
