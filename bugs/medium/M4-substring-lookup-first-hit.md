# M4 — Substring (`in`) matching returns the first partial hit in NBR 6120 lookups

**Severity:** MEDIUM
**Location:** `table_10/model.py:29,60`, `table_2/model.py:77`, `table_4/model.py:58`, `table_7/model.py:41`, `table_8/model.py:39`

## Diagnosis
Lookups do `if query in candidate.description.lower()` and return the first hit. When
one description is a substring of another (or a short query is passed), the first row in
tuple order shadows the intended, more specific one.

## Impact
Latent wrong-load / wrong-material selection if a caller passes a non-unique substring,
or a future table has overlapping names.

## Suggested fix
Prefer case-insensitive exact equality with substring as explicit fallback; raise if
more than one entry matches.
