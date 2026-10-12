# Beam Calculator — Bug & Inconsistency Index

Each bug is its own file under `critical/`, `high/`, `medium/`, `low/`. Findings came
from a line-by-line review of every `src/` module, spot-verified against the source.
Fixed, stale and not-a-bug reports are deleted (git history keeps the diagnosis), so
numbering has gaps.

**Totals:** 0 critical · 1 high · 1 medium · 0 low.

## CRITICAL — wrong result or crash on a normal input path

- None open.

## HIGH — wrong result on a reachable path, or a latent 10× trap

- [H8](high/H8-no-end-support-anchorage.md) — No end-support anchorage: bars near a beam end cannot be detailed

## MEDIUM — correctness risk under specific inputs, or unconservative simplification

- [M2](medium/M2-nominal-covering-global-concrete.md) — `nominal_covering` uses global concrete, not the element's *(latent)*

## LOW — documentation / typing / dead code, no runtime effect

- None open.

## Suggested fix order

1. **H8** — end-support anchorage (`src/examples/pavement/t_concreto2.py` still fails on V4).
2. **M2** — latent item.
