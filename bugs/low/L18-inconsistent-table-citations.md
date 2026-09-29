# L18 — Inconsistent NBR 6118 table citations for load combinations

**Severity:** LOW
**Location:** `src/loading/forces.py:16,84,102`

## Diagnosis
The same γf=1.4 constant is cited as Table 11.1 (line 16) and Table 11.3 (line 102); the
quasi-permanent ψ₂ values are attributed to Table 11.4 (line 84) when the CQP factors are
in Table 11.2. Documentation inconsistency.

## Impact
Documentation inconsistency; no runtime effect.

## Suggested fix
Reconcile to one correct citation each (keep `# PAPER` tags if unverified).
