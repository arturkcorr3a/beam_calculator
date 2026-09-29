# L10 — Int/float annotation drift in centroid helpers

**Severity:** LOW
**Location:** `src/reinforcement/reinforcement.py:155–166,252–259`

## Diagnosis
`weighted_centroids`/`weights` init as `int` `0`; the zero-weight branch returns
`(0, 0)` while the annotation is `tuple[float, float]`. Strict-typing nit.

## Impact
Type-checker nit; no runtime effect.

## Suggested fix
Initialise `0.0`, return `(0.0, 0.0)`.
