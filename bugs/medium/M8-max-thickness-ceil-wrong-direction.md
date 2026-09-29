# M8 — `max_thickness` rounds the upper limit up (`ceil`), permitting over-limit slabs

**Severity:** MEDIUM
**Location:** `src/pavement_elements/slab.py:318–323`

## Diagnosis
`max_thickness = ceil(min(dimensions)/3)` (§14.4.2.1 gives h ≤ ℓ/3). Rounding an upper
bound *up* is the wrong direction (min_dim=100 → limit 33.3, ceil→34), permitting a
thickness slightly above the true limit.

## Impact
Off-by-one on the limit in the unconservative direction.

## Suggested fix
`math.floor(min(self.dimensions) / 3)`.
