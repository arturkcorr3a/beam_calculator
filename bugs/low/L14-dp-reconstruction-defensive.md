# L14 — `choose_best_combination` DP reconstruction lacks a defensive check

**Severity:** LOW
**Location:** `src/reinforcement/rebar_chooser.py:112–118`

## Diagnosis
If `previous[slot]` were ever `-1`, `rebars[-1]` silently takes the *last* rebar instead
of erroring. Invariants make this unreachable today, but it is silent-wrong if they ever
break.

## Impact
Latent; silent-wrong reconstruction rather than an exception.

## Suggested fix
`assert rebar_index != -1` inside the loop.
