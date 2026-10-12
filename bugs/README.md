# Beam Calculator — Bug & Inconsistency Index

Each bug is its own file under `critical/`, `high/`, `medium/`, `low/`. Findings came
from a line-by-line review of every `src/` module, spot-verified against the source.
Fixed, stale and not-a-bug reports are deleted (git history keeps the diagnosis), so
numbering has gaps.

**Totals:** 0 critical · 1 high · 7 medium · 0 low.

## CRITICAL — wrong result or crash on a normal input path

- None open.

## HIGH — wrong result on a reachable path, or a latent 10× trap

- [H8](high/H8-no-end-support-anchorage.md) — No end-support anchorage: bars near a beam end cannot be detailed

## MEDIUM — correctness risk under specific inputs, or unconservative simplification

- [M2](medium/M2-nominal-covering-global-concrete.md) — `nominal_covering` uses global concrete, not the element's *(latent)*
- [M7](medium/M7-pick-best-option-empty-indexerror.md) — `_pick_best_option` bare `IndexError` when infeasible
- [M8](medium/M8-max-thickness-ceil-wrong-direction.md) — `max_thickness` rounds the limit the wrong way
- [M9](medium/M9-presize-loop-no-guard.md) — Slab pre-sizing fixed-point loop has no convergence guard
- [M14](medium/M14-global-id-counters.md) — Process-global ID counters; reload doesn't keep saved IDs
- [M15](medium/M15-hardcoded-fixed-ratio-threshold.md) — Hardcoded `0.8` instead of `FIXED_RATIO_THRESHOLD`
- [M16](medium/M16-layer-centroid-excludes-cover.md) — `Layer.y_centroid_position` excludes cover and stirrup

## LOW — documentation / typing / dead code, no runtime effect

- None open.

## Suggested fix order

1. **H8** — end-support anchorage (`src/examples/pavement/t_concreto2.py` still fails on V4).
2. **M16** — wrong bond zone in anchorage (`has_good_adherence`); remove the GUI shift
   in `reinforcement_reader.py` together with the fix.
3. **M7, M8, M9** — infeasible-shear error, thickness limit, iteration cap.
4. **M14, M15** — ID reproducibility on reload, named constant.
5. **M2** — latent item.
