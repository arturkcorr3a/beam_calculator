# BUG-003 — `design_load` mutates `permanent_load` on every property access

| Field | Value |
|---|---|
| **ID** | BUG-003 |
| **Severity** | 🟡 Medium |
| **Status** | Open |
| **File** | `src/checkers/slab_deformation_checker.py` |
| **Lines** | 69–79 |
| **Method** | `SlabDeformationChecker.design_load` |

## Description

The `design_load` property adds the slab self-weight to `self.permanent_load`
every time it is called, causing the permanent load to accumulate across calls.
Since `design_load` is accessed at least twice during a single `verify()` call
(once inside `service_moment` and once inside `immediate_deflection`), the
self-weight is double-counted on the second call.

## Root Cause

```python
# slab_deformation_checker.py, lines 70–73
@property
def design_load(self) -> float:
    self.permanent_load = (            # ← mutates instance state
        self.permanent_load
        + SuperficialLoads.get_concrete_element_own_weight(self.height / 100.0)
    )
    load_kn_m2 = almost_permanent_combination_els(
        self.permanent_load, self.variable_load, self.usage
    )
    ...
```

A `@property` with side-effects on `self` is dangerous: callers reasonably assume
repeated access is idempotent. The call sequence within a single `verify()`:

1. `service_moment` → accesses `design_load` → `permanent_load += own_weight` ✅
2. `is_cracked` → accesses `service_moment` → accesses `design_load` → `permanent_load += own_weight` again ❌
3. `immediate_deflection` → accesses `design_load` → `permanent_load += own_weight` again ❌

Each subsequent call inflates the load, producing a progressively higher (and
incorrect) `design_load`.

## Fix

Compute the total permanent load into a local variable without mutating `self`:

```python
@property
def design_load(self) -> float:
    total_permanent = (
        self.permanent_load
        + SuperficialLoads.get_concrete_element_own_weight(self.height / 100.0)
    )
    load_kn_m2 = almost_permanent_combination_els(
        total_permanent, self.variable_load, self.usage
    )
    design_load = load_kn_m2 / 10_000
    log_operation(f"Design load = {design_load:.6f} kN/cm²")
    return design_load
```

Alternatively, add the own-weight once in `verify()` before the calculation loop,
or cache `design_load` as a `@functools.cached_property` (valid only if `height`
does not change within a single verification).

