# L17 — `is_concrete_greater_than_minimum` uses strict `>` — verify intent

**Severity:** LOW
**Location:** `src/config.py:38–53`

## Diagnosis
`return fck > 30` etc. means fck exactly at the class minimum returns False. The adjacent
TODO suggests the intended semantic may be "fck ≥ minimum". The method name is internally
consistent with `>`; flag to confirm against NBR 6118 §7.4.2 / Table 7.1 before changing.

## Impact
A borderline concrete class (fck exactly at the class minimum) could be
rejected/accepted incorrectly wherever this is consumed.

## Suggested fix
Confirm normative intent; if "acceptable when fck ≥ minimum", use `>=` and rename
accordingly.
