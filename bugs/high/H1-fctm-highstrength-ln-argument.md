# H1 — `fct_m` high-strength branch uses the wrong argument inside `ln`

**Severity:** HIGH
**Location:** `src/properties/concrete.py:188`

## Diagnosis
For `fck > 50` the code computes `2.12 * log(1 + 0.1 * (self.value + 8)) / 10`.
NBR 6118 §8.2.5 gives `f_ct,m = 2.12 · ln(1 + 0.11 · f_ck)`. `0.1·(fck+8) = 0.1·fck
+ 0.8` is **not** `0.11·fck` (e.g. fck=60 → code arg 7.8 vs correct 7.6). Almost
certainly a transcription error.

## Impact
For C55–C90, `fct_m` and everything derived from it (`fctk_sup`, `fctk_inf`, `fctd`,
bond strength, min stirrup ratio, min rebar, cracking moment) is slightly off (~2%).
Only affects high-strength concrete; low-strength branch (≤ C50) is correct.

## Suggested fix
`(2.12 * log(1 + 0.11 * self.value)) / 10`. Confirm against the NBR 6118 edition in
use before committing.
