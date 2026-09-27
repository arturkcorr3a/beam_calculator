# M14 — Process-global ID counters shared across `Pavement` instances

**Severity:** MEDIUM
**Location:** `pillar.py:27`, `continuous_beam.py:71`, `slab.py:102`

## Diagnosis
`_counter = count(1)` at class scope means P/V/L IDs never reset between two `Pavement`
objects in one process (tests, batch runs).

## Impact
Non-reproducible IDs across runs; test flakiness.

## Suggested fix
Reset counters per pavement, or inject IDs.
