# H3 — ConfigDialog writes to non-existent `AppConfig` fields; beam-default combos are dead

**Severity:** HIGH
**Location:** `src/gui/pavement_gui.py:1303–1305`, `1312–1314`

## Diagnosis
The "BEAM DEFAULTS" combos connect to `setattr(APP_CONFIG, "default_concrete", v)` and
`setattr(APP_CONFIG, "steel", v)`. Neither `default_concrete` nor `steel` is a field of
`AppConfig` — `setattr` silently creates junk attributes nothing reads. The same combos
*initialise* from `pavement_concrete`/`pavement_steel` (lines 1302, 1311), so they
duplicate the pavement controls.

## Impact
User-facing "beam default" concrete/steel edits are silently discarded. Also violates
the AGENTS.md AppConfig↔persistency contract by referencing config fields that don't
exist.

## Suggested fix
Point both combos at real fields (`pavement_concrete`/`pavement_steel`), or add genuine
`default_concrete`/`default_steel` fields to `AppConfig` **and** mirror them in
`schema.py` / `serialization.py` / `deserialization.py` per the sync rule.
