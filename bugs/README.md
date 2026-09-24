# Known Bugs

Bugs found during code review of the ELS-DEF (Serviceability Limit State of Excessive
Deformation) implementation for solid slabs.

Review based on:
- **ABNT NBR 6118:2026** — Sections 8.2.5, 8.2.8, 13.3, 17.3.1, 17.3.2.1.1, 17.3.2.1.2
- **Carvalho & Figueiredo Filho** — *Cálculo e Detalhamento de Estruturas Usuais de
  Concreto Armado*, Sections 7.3.7.2.1

## Open Bugs

| ID | Severity | File | Method | Summary |
|---|---|---|---|---|
| [BUG-001](BUG-001-immediate-deflection-missing-width.md) | 🔴 Critical | `slab_deformation_checker.py:98` | `immediate_deflection` | Missing `self.width` (100 cm) factor in elastic deflection numerator — result is 100× too small |
| [BUG-002](BUG-002-long-term-factor-delta-xi.md) | 🔴 Critical | `deformation_checker.py:147` | `long_term_deflection` | Uses `ξ(∞) = 2.0` instead of `Δξ = ξ(∞) − ξ(t₀) = 1.47` — overstates long-term deflection by ~21% |
| [BUG-003](BUG-003-design-load-state-mutation.md) | 🟡 Medium | `slab_deformation_checker.py:70` | `design_load` | Self-weight added to `self.permanent_load` on every property access — accumulates on repeated calls |
| [BUG-004](BUG-004-tensioned-area-uses-minimum-moment.md) | 🟠 Low–Med | `slab_deformation_checker.py:197` | `_tensioned_reinforcement_area` | Rebar area computed from minimum moment (`md_min`), not actual service moment — conservative but undocumented |

## Severity Legend

| Icon | Level | Meaning |
|---|---|---|
| 🔴 | Critical | Produces an incorrect numerical result that could mask a real structural failure |
| 🟡 | Medium | Incorrect behavior under repeated calls or specific conditions |
| 🟠 | Low–Med | Intentionally conservative but undocumented; may mislead future maintainers |

