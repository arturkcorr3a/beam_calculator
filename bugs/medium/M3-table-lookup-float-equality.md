# M3 — Table lookups use exact float `==` for thickness keys

**Severity:** MEDIUM
**Location:** `src/data/nbr6120_2019/table_2/model.py:42` (`MasonryType.get_thickness`),
`src/data/nbr6120_2019/table_4/model.py:27` (`CoveringMaterial.get_weight`)

## Diagnosis
Thickness keys are compared with `float == float`. Values that arrive from spin boxes
or from cm↔m arithmetic can be off by an epsilon and miss an entry that is "obviously"
present, which gives a spurious `ValueError`. The Carvalho tables already use
`isclose`; these don't.

## Impact
Occasional spurious "not found" errors; brittle.

## Suggested fix
`math.isclose(a, b, abs_tol=1e-9)`. Caveat: in Table 4, `thickness_cm` is
`float | None` (entries without a thickness), so keep an explicit `None == None` match
before calling `isclose`.
