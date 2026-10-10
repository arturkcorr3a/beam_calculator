# Beam Calculator — Bug & Inconsistency Index

Each bug is its own file under `critical/`, `high/`, `medium/`, `low/`. Findings came
from a line-by-line review of every `src/` module, then spot-verified against the source
where severity was high (a few over-stated items were downgraded — see L1).

**Totals:** 3 critical · 7 high · 15 medium · 18 low.

## CRITICAL — wrong result or crash on a normal input path
- [C2](critical/C2-slab-edge-division-by-zero.md) — Slab-edge support resolution divides by zero (no spans)
- [C3](critical/C3-psi2-factor-noop.md) — Quasi-permanent ELS factor ψ₂ is a no-op (always 0.30)
- [C4](critical/C4-slab-own-weight-not-unloaded.md) — Slab self-weight is never transferred to the supporting beams

## HIGH — wrong result on a reachable path, or a latent 10× trap
- [H1](high/H1-fctm-highstrength-ln-argument.md) — `fct_m` high-strength branch uses wrong `ln` argument
- [H2](high/H2-steel-elastic-modulus-unit-trap.md) — Steel `elastic_modulus` labelled kN/cm² but is MPa
- [H3](high/H3-config-dialog-nonexistent-fields.md) — ConfigDialog writes to non-existent AppConfig fields
- [H4](high/H4-moment-shift-division-by-zero.md) — `calculate_moment_shift` divides by zero when V_Sd ≤ V_c
- [H5](high/H5-carvalho-table7-muy-outlier.md) — Carvalho Quadro 7.1 `mu_y` data outlier (3.14)
- [H6](high/H6-pillars-touching-beam-straddle.md) — `_pillars_touching_beam` misses a straddling pillar
- [H7](high/H7-slab-equality-vs-identity.md) — `==` vs `is` on `Slab` dataclasses

## MEDIUM — correctness risk under specific inputs, or unconservative simplification
- [M1](medium/M1-slab-effective-depth-discount.md) — Slab effective-depth discount uses 1.5× bar diameter
- [M2](medium/M2-nominal-covering-global-concrete.md) — `nominal_covering` uses global concrete, not the beam's
- [M3](medium/M3-table-lookup-float-equality.md) — Table lookups use exact float `==`
- [M4](medium/M4-substring-lookup-first-hit.md) — Substring matching returns first partial hit
- [M5](medium/M5-default-distance-d-too-small.md) — `DEFAULT_DISTANCE_FOR_D_CALCULATION` too small
- [M6](medium/M6-distribute-bars-layer-advance.md) — `distribute_bars_in_layers` forces a layer advance
- [M7](medium/M7-pick-best-option-empty-indexerror.md) — `_pick_best_option` bare `IndexError` when infeasible
- [M8](medium/M8-max-thickness-ceil-wrong-direction.md) — `max_thickness` rounds the limit the wrong way
- [M9](medium/M9-presize-loop-no-guard-stale-conditions.md) — Slab pre-sizing loop: no cap, stale conditions
- [M10](medium/M10-rebar-convergence-no-cap.md) — Rebar convergence loop has no iteration cap
- [M11](medium/M11-actual-y-negative-sqrt.md) — `actual_y` can hit `sqrt` of a negative number
- [M12](medium/M12-influence-areas-yield-line-heuristic.md) — Yield-line pattern from a single-coordinate test
- [M13](medium/M13-elu-combination-single-gamma.md) — `normal_elu_combination` single γ=1.4, ignores ψ₀
- [M14](medium/M14-global-id-counters.md) — Process-global ID counters shared across pavements
- [M15](medium/M15-hardcoded-fixed-ratio-threshold.md) — Hardcoded `0.8` instead of `FIXED_RATIO_THRESHOLD`

## LOW — documentation / typing / dead code, no runtime effect
- [L1](low/L1-fctm-mpa-comment.md) — Misleading `# MPa` comment on `fct_m` (math is correct)
- [L2](low/L2-d-compressed-copypaste-message.md) — Copy-pasted error message in `d_compressed`
- [L3](low/L3-slab-validate-beam-message.md) — Copy-pasted "Beam" in `Slab._validate_pillars_exist`
- [L4](low/L4-effective-depth-compressed-unit.md) — `effective_depth_compressed` unit `cm²` (is cm)
- [L5](low/L5-bond-strength-docstring-unit.md) — `design_bond_strength` docstring unit "kN/cm"
- [L6](low/L6-eci-docstring-aggregate.md) — `eci` docstring hardcodes aggregate type
- [L7](low/L7-beam-length-docstring-unit.md) — Beam `length` docstring says metres; code uses cm
- [L8](low/L8-layer-centroid-docstring-unit.md) — Layer centroid docstring says "mm" (computes cm)
- [L9](low/L9-stirrups-max-diameter-docstring.md) — `stirrups.max_diameter` docstring overstates logic
- [L10](low/L10-centroid-int-float-drift.md) — Int/float annotation drift in centroid helpers
- [L11](low/L11-rebar-choice-options-type-drift.md) — `rebar_choice_options` changes type
- [L12](low/L12-qwidget-optional-annotation.md) — `parent: QWidget = None` should be `QWidget | None`
- [L13](low/L13-support-py-dead-code.md) — Fully commented-out dead file `support.py`
- [L14](low/L14-dp-reconstruction-defensive.md) — DP reconstruction lacks a defensive check
- [L15](low/L15-report-exporter-makedirs.md) — `report_exporter` `makedirs` fragile on odd paths
- [L16](low/L16-logger-frame-introspection.md) — `logger._log` frame introspection + missing DISABLED style
- [L17](low/L17-concrete-minimum-strict-comparison.md) — `is_concrete_greater_than_minimum` strict `>`
- [L18](low/L18-inconsistent-table-citations.md) — Inconsistent NBR 6118 table citations

## Suggested fix order
1. **C2, C3, C4** — crash and unconservative loads on normal paths.
2. **H4, H1, H5** — shear-design crash, high-strength formula error, table outlier.
3. **H2, H3** — the 10× documentation trap and the dead/incorrect config combos.
4. **H6, H7, M1, M2** — geometry/validation gaps and the effective-depth biases.
5. Remaining **M** items (iteration caps, lookups, packing), then the **L** cleanups.
