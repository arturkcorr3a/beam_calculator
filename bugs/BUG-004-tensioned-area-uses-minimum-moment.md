# BUG-004 — `_tensioned_reinforcement_area` always uses the minimum design moment

| Field | Value |
|---|---|
| **ID** | BUG-004 |
| **Severity** | 🟠 Low–Medium |
| **Status** | Open |
| **File** | `src/checkers/slab_deformation_checker.py` |
| **Lines** | 172–201 |
| **Method** | `SlabDeformationChecker._tensioned_reinforcement_area` |

## Description

The tensioned reinforcement area `A_s` fed into Branson's formula is computed from
the **minimum design moment** (`md_min`) rather than from the actual service
moment. For slabs with higher loading, the actual reinforcement is larger,
yielding a stiffer cracked section (`I_II`) and a smaller deflection — so this
approach is always **conservative** but not physically representative.

## Root Cause

```python
# slab_deformation_checker.py, lines 189–199
calculator = RebarCalculator(
    beam=dummy_beam,
    bending_moment=0,          # ← actual service moment not used
    ...
)
calculator.design_bending_moment = md_min   # ← overridden with minimum moment
calculator.d = self.effective_depth
calculated_min = calculator.as1             # A_s for md_min only
```

The `RebarCalculator` is set up with `md_min` regardless of what moment the slab
actually experiences. This means:

- `x_II` (neutral axis depth) is underestimated.
- `I_II` (cracked inertia) is underestimated.
- `I_eq` from Branson's formula is underestimated.
- `f_immediate` is overestimated (conservative deflection).

In the pre-sizing context this is acceptable as a safe lower bound for `I_II`,
but it should be explicitly documented so future maintainers understand why the
actual `service_moment` is not being used here.

## Recommended Action

Add a clear comment explaining the design decision:

```python
# NOTE: During pre-sizing, the actual rebar area is unknown.
# We use the minimum moment (md_min) to obtain a lower-bound rebar area,
# which yields a conservative (higher) deflection estimate via Branson's formula.
# Once the final reinforcement is determined, this should be replaced with
# the actual As to get an accurate I_eq.
calculator.design_bending_moment = md_min
```

If an accurate deflection check after final design is ever needed, `A_s` should
be passed in as a constructor parameter to `SlabDeformationChecker` rather than
being derived internally.

