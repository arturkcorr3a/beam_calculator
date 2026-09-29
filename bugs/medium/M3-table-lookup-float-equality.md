# M3 — Table lookups use exact float `==` for thickness keys

**Severity:** MEDIUM
**Location:** `src/data/nbr6120_2019/table_2/model.py:42`, `src/data/nbr6120_2019/table_4/model.py:27`

## Diagnosis
Thickness keys compared with `float == float`. Values arriving from spin boxes or cm↔m
arithmetic can be off by an epsilon and miss an entry that is "obviously" present →
spurious `ValueError`. The Carvalho tables already use `isclose`; these don't.

## Impact
Occasional spurious "not found" errors; brittle.

## Suggested fix
`math.isclose(a, b, abs_tol=1e-9)`.
