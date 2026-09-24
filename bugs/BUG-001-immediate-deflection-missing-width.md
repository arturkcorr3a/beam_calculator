# BUG-001 — Missing strip width factor in `immediate_deflection`

| Field | Value |
|---|---|
| **ID** | BUG-001 |
| **Severity** | 🔴 Critical |
| **Status** | Open |
| **File** | `src/checkers/slab_deformation_checker.py` |
| **Lines** | 98–101 |
| **Method** | `SlabDeformationChecker.immediate_deflection` |

## Description

The elastic deflection formula for a slab strip is missing the strip **width** factor
(`b = 100 cm`) in the numerator, causing the computed deflection to be 100× too small.

## Root Cause

The Carvalho & Figueiredo Filho formula (Section 7.3.7.2.1, Eq. 7.16) is defined
for a **1 m = 100 cm wide strip**:

$$f_{elast} = \frac{p_{qp} \cdot b \cdot \ell_x^4}{E_{cs} \cdot h^3} \cdot \frac{\alpha}{100}$$

`design_load` is in **kN/cm²** (force per unit area). To obtain a force per unit
length (kN/cm), it must be multiplied by the strip width `b` (cm).
The implementation omits this multiplication:

```python
# slab_deformation_checker.py, lines 98–101
elastic_deflection = (
    (self.design_load * self.span**4)   # ← missing * self.width
    / (ecs_kn_cm2 * self.height**3)
    * (alpha / 100)
)
```

Because `self.width = 100.0`, the result is exactly **100× smaller** than the
correct value — the slab always appears to deflect much less than it actually does,
masking real ELS-DEF failures.

## Fix

```python
elastic_deflection = (
    (self.design_load * self.width * self.span**4)  # add self.width
    / (ecs_kn_cm2 * self.height**3)
    * (alpha / 100)
)
```

## Reference

- Carvalho & Figueiredo Filho — *Cálculo e Detalhamento de Estruturas Usuais de
  Concreto Armado*, Section 7.3.7.2.1, Eq. 7.16 (p. 331).

