# H8 — No end-support anchorage: bars near a beam end cannot be detailed

**Severity:** HIGH
**Location:** `src/calculators/anchorage_calculator.py` (`AnchorageCalculator.run`),
`src/reinforcement/reinforcement.py` (`_run_anchorage_calculation`)

## Diagnosis

Every bar is extended from its interest point by `a_l + l_b,nec` on each side, and the
combination is rejected when that extent does not fit before the beam end (even with
hooks). There is no end-support anchorage model: a positive-moment bar whose extent
crosses an end support should stop at the support and be anchored there for the force
`R_st = (a_l / d) · V_d`, with `l_b,nec ≥ max(r + 5.5φ, 6 cm)` (ABNT NBR 6118:2014 —
Section 18.3.2.4.1).

Exposed by the H4 fix: with `V_Sd ≤ V_c`, `a_l = d` (it used to collapse to `0.5d`), so
the required extent grows.

## Impact

`src/examples/t_concreto2.py` fails on V4: the bottom bars at x = 1966.7 cm
need ≈ 66 cm to the right but only 53.8 cm remain → `No valid reinforcement combination
found.` Any short end region with low shear can hit the same failure.

## Suggested fix

When a bar's extent crosses a beam end, stop it at the support (minus cover) and verify
the end-support anchorage per §18.3.2.4.1 instead of the full `a_l + l_b,nec`, allowing
hooks.
