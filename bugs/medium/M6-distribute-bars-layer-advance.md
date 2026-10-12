# M6 — `_add_rebar_to_layers` forces a layer advance when the group fits wholesale

**Severity:** MEDIUM
**Location:** `src/reinforcement/reinforcement.py:303–336` (`distribute_bars_in_layers`, `_add_rebar_to_layers`)

## Diagnosis
When a whole `bars_to_add` group fits in the current layer (lines 313–317),
`_add_rebar_to_layers` returns `current_layer + 1`. This advances even if the layer
still has room for the next (smaller) group. The bar-by-bar fallback (lines 319–331)
only advances on failure and returns the layer it ended in. The two paths use
inconsistent layer-advancement policies, and the "across N layers" log (333–335) can
misreport.

## Impact
Suboptimal packing (more layers than needed), possibly triggering a false
"Cannot distribute bars within the maximum number of layers" `ValueError`.

## Suggested fix
Reconcile the two strategies: return `current_layer` after a wholesale fit, and let
the next group advance only when it doesn't fit.
