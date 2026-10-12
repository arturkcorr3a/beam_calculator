# M4 — Substring (`in`) matching returns the first partial hit in NBR 6120 lookups

**Severity:** MEDIUM (latent)
**Location:** `src/data/nbr6120_2019/`
- `table_2/model.py:75–77` (`find_masonry_type`)
- `table_4/model.py:56–58` (`find_material`)
- `table_7/model.py:39–41` (`find_material`)
- `table_8/model.py:37–39` (`find_material`)
- `table_10/model.py:27–29` (`get_location_load`), `58–60` (`find_category`)

## Diagnosis
Lookups do `if query in candidate.description.lower()` and return the first hit. When
one description is a substring of another, an exact query for the longer one is still
fine. An exact query for the shorter one is shadowed only if the longer entry comes
first.

Currently **no shadowing occurs**. The only overlaps are:
- Table 7: "expanded clay" ⊂ "lightweight concrete (with expanded clay)"
- Table 10 (Technical areas): "header pipe area" ⊂ "general technical areas (…),
  except header pipe area"

In both, the shorter entry comes first. Production callers (`superficial_loads.py`,
`linear_loads.py`, `options_reader.py`) pass full descriptions.

## Impact
Latent wrong-load / wrong-material selection if table data is reordered or extended
with overlapping names.

## Suggested fix
Try an exact case-insensitive match first, then fall back to substring matching.
Ideally do this in one shared helper used by all six lookups. Do **not** raise on
ambiguous substrings: tests rely on first-hit on purpose
(`test_first_match_returned_for_ambiguous_query` with "ceiling"; "residential" also
matches "Non-residential laundries").
