# L9 — `stirrups.max_diameter` docstring overstates its logic

**Severity:** LOW
**Location:** `src/reinforcement/stirrups.py:30–37`

## Diagnosis
Docstring says the max is "based on required ratio and minimum spacing," but the code
just returns `beam.width/10` (φt ≤ bw/10, §18.3.3.2 — the correct value).

## Impact
Documentation only.

## Suggested fix
Correct the docstring.
