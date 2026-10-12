# M14 — Process-global ID counters shared across `Pavement` instances

**Severity:** MEDIUM
**Location:** `src/pavement_elements/pillar.py:41`, `src/pavement_elements/continuous_beam.py:86`,
`src/pavement_elements/slab.py:116`; consumed by `src/persistency/deserialization.py:111–200,224–258`

## Diagnosis
`_counter = count(1)` at class scope means P/V/L IDs never reset between two `Pavement`
objects in one process. IDs can now be injected (`id=` kw-only field), and the UI's
`pavement_ui/core/engine/element_factory.py` passes them. However,
`deserialization.py` (`_pillar_from_dict`, `_beam_from_dict`, `_slab_from_dict`) does
not pass the saved ID: every load draws fresh numbers from the global counter.
`id_map`/`remap` keep pillar references consistent, but the user-visible IDs change.
They are P1…Pn in a fresh process and shifted numbers after another pavement has
been built.

## Impact
Non-reproducible IDs across loads and runs: a saved and reloaded file may not show
the same element names. Possible flakiness in tests that assert IDs.

## Suggested fix
Pass the saved `id` through in deserialization (the `remap` indirection then becomes
the identity), and/or reset the counters per pavement.
