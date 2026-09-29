# M6 — `distribute_bars_in_layers` forces a layer advance when the group fits wholesale

**Severity:** MEDIUM
**Location:** `src/reinforcement/reinforcement.py:282–307`

## Diagnosis
When a whole `bars_to_add` group fits (line 284) it returns `current_layer + 1`,
advancing even if the current layer still has room for the next (smaller) group. The
bar-by-bar fallback (lines 290–302) advances on failure instead — the two paths use
inconsistent layer-advancement policy. Layer count log (304–306) can misreport.

## Impact
Suboptimal packing (more layers than needed), possibly triggering false "cannot
distribute within max layers" `ValueError`.

## Suggested fix
Reconcile the two strategies; don't force an advance when the current layer has
capacity.
