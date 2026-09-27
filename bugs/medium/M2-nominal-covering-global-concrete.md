# M2 — `nominal_covering` uses global `APP_CONFIG` concrete, not the beam's own

**Severity:** MEDIUM
**Location:** `src/structural_elements/rectangular_beam.py:27–52` (consumed at `reinforcement.py:116,122,350`)

## Diagnosis
The "concrete greater than minimum" cover discount reads `APP_CONFIG.pavement_concrete`,
not `self.concrete`. A beam built with a concrete class different from the configured
pavement concrete gets the wrong fck for the cover discount.

## Impact
Wrong nominal cover (±0.5 cm) → wrong effective depth & anchorage space when beam
concrete ≠ configured pavement concrete.

## Suggested fix
Make `nominal_covering` an instance property that reads `self.concrete`.
