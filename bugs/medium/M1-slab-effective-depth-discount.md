# M1 — Slab effective-depth discount `covering + 1.5·φ` is undocumented

**Severity:** LOW (was MEDIUM)
**Location:** `src/checkers/slab_deformation_checker.py:26–33` (`_default_effective_depth_discount`)

## Diagnosis
Returns `Slab.nominal_covering + 1.5 * rebar_discount_10_mm` (= cover + 1.5 cm) for
an assumed φ10 mm bar. This was first reported as an over-discount (a single layer
would sit at cover + φ/2). It is more likely the usual convention for the **inner** of
the two orthogonal bar layers of a two-way slab: cover + φ (outer layer) + φ/2. The
real defect is that the convention is neither documented nor referenced.

## Impact
None if the convention is intended (effective depth of the inner layer, the
conservative choice). It is hard to audit as written.

## Suggested fix
Add a comment that explains the convention (inner layer: c + φ + φ/2) and tag it
`# PAPER` until a reference is found (e.g. Carvalho & Figueiredo Filho). Name the
magic `1` as the assumed bar diameter in cm.
