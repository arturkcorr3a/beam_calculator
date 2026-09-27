# H5 — Table 7 (Carvalho Quadro 7.1) data outlier: `mu_y` at λ=1.60, case 1

**Severity:** HIGH
**Location:** `src/data/carvalho/table_7/data.py:193`

## Diagnosis
`MomentCoefficients(8.34, 3.14)`. The case-1 `mu_y` column is smooth and monotone
around this row (…4.30, 4.25, 4.20, **3.14**, 4.07, 4.00…); 3.14 breaks the trend by
~1.0 and is almost certainly a transcription error for ~4.14. (File carries a "TODO
review values one by one".)

## Impact
Two-way slabs with aspect ratio ≈ [1.55, 1.65], case 1, get a badly wrong `mu_y` →
wrong `My` and slab reinforcement. Structural correctness.

## Suggested fix
Verify against Quadro 7.1 (Carvalho & Figueiredo Filho, 2014, ~p.326); likely 4.14.
**Do not change without confirming the source.**
