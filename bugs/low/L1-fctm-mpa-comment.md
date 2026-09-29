# L1 — Misleading `# MPa` comment on `fct_m` in the min stirrup ratio

**Severity:** LOW
**Location:** `src/calculators/stirrup_calculator.py:106`

## Diagnosis
Comment says `fct_m  # MPa`, but `concrete.fct_m` returns **kN/cm²** (both branches
divide by 10, `concrete.py:186,188`). The computation `0.2 * fct_m / fywk * bw` is
therefore **dimensionally consistent and correct** (both operands kN/cm²) — only the
comment is wrong.

> Note: an earlier review flagged this as a 10× safety error; verification against the
> source shows the math is correct — the defect is the comment alone.

## Impact
None on results; misleads maintainers.

## Suggested fix
Change the comment to `# kN/cm²`.
