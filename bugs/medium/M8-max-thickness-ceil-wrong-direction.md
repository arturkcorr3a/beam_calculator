# M8 — `max_thickness` rounds the upper limit up (`ceil`), permitting over-limit slabs

**Severity:** MEDIUM
**Location:** `src/pavement_elements/slab.py:522–527` (consumed by `pre_size` at `slab.py:276`)

## Diagnosis
`max_thickness = ceil(min(self.effective_dimensions) / 3)` (§14.4.2.1 gives h ≤ ℓ/3).
Rounding an upper bound *up* is the wrong direction (ℓ = 100 → limit 33.3, ceil → 34),
so it permits a thickness slightly above the true limit.

## Impact
Off-by-one on the limit in the unconservative direction.

## Suggested fix
`math.floor(min(self.effective_dimensions) / 3)`.
