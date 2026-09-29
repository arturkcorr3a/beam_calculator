# H7 — `==` vs `is` on `Slab` dataclasses in span support resolution

**Severity:** HIGH
**Location:** `src/pavement_elements/beam_span.py:48–57`, `59–66`

## Diagnosis
`Slab` is a `@dataclass` (default `eq=True`), so `==` compares by field *values*, not
identity. `get_other_supported_slab` / `add_supported_slab` use `==` on slab objects;
two distinct slabs with equal fields compare equal, and the comparison may touch
cached_property state. "Other slab" resolution can bind the wrong slab.

## Impact
Wrong support-condition resolution when two slabs share dimensions.

## Suggested fix
Compare with `is`, or declare `Slab` with `eq=False`.
