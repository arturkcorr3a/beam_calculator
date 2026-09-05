"""
Manual test: pre-sizing a 3×3 grid of 9 slabs.

Grid layout (coordinates and IDs shown at pillar intersections):

    P13----V10----P14----V11----P15----V12----P16
    |      (TOP)  |      (TOP)  |      (TOP)  |
    V7           V8            V9             |
   (LEFT)       (INT)         (INT)         (RIGHT)
    |             |             |             |
    P9-----V7----P10----V8-----P11----V9-----P12
    |      (MID)  |      (MID)  |      (MID)  |
    V4           V5            V6             |
   (LEFT)       (INT)         (INT)         (RIGHT)
    |             |             |             |
    P5-----V4----P6-----V5-----P7-----V6-----P8
    |      (BOT)  |      (BOT)  |      (BOT)  |
    V1           V2            V3             |
   (LEFT)       (INT)         (INT)         (RIGHT)
    |             |             |             |
    P1-----V1----P2-----V2-----P3-----V3-----P4
           (BOTTOM)

9 slabs arranged in a 3-column × 3-row grid:
  Row 1 (bottom): L1, L2, L3
  Row 2 (middle): L4, L5, L6
  Row 3 (top):    L7, L8, L9

Panel spans are non-uniform — the middle column and middle row are wider so
the central slabs require more thickness iterations:

  Column widths (x):  380 cm | 620 cm | 380 cm
  Row heights   (y):  330 cm | 580 cm | 330 cm

  L1 / L3 / L7 / L9 (corners):  380×330 cm  → h ≈ 8 cm
  L2 / L8  (top/bottom centre): 620×330 cm  → several iterations
  L4 / L6  (left/right centre): 380×580 cm  → several iterations
  L5 (centre):                  620×580 cm  → most iterations

Beam width: 16 cm, pillar sections: 20×20 cm throughout.
Mixed usages to exercise different variable loads.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from src.loading.superficial_loads import SuperficialLoads
from src.pavement.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement.geometry_utils import Alignment
from src.pavement.pavement import Pavement
from src.pavement.pillar import Pillar
from src.pavement.slab import Slab, SLAB_MIN_THICKNESS, SLAB_MAX_THICKNESS
from src.config import APP_CONFIG
from src.properties.concrete import Concrete

# Non-uniform panel spans (cm): narrow outer panels, wide middle panels
# so the central slabs require more thickness iterations.
COLUMN_WIDTHS = [380, 620, 380]  # x-span per column panel (3 gaps → 4 pillar columns)
ROW_HEIGHTS   = [330, 580, 330]  # y-span per row panel    (3 gaps → 4 pillar rows)

# Cumulative pillar coordinates (cm)
PILLAR_X_COORDS = [sum(COLUMN_WIDTHS[:i]) for i in range(len(COLUMN_WIDTHS) + 1)]
PILLAR_Y_COORDS = [sum(ROW_HEIGHTS[:i])   for i in range(len(ROW_HEIGHTS) + 1)]

BEAM_WIDTH = 16
PILLAR_DIM = 20

# Grid: 4 columns × 4 rows of pillars → 3×3 panels
N_COLS = 4
N_ROWS = 4

# Slab usages (row-major order: bottom-left first)
SLAB_LOCALS = [
    "Bedrooms",                              # L1 — bottom-left
    "Living rooms, pantries, and kitchens",  # L2
    "Bathrooms",                             # L3 — bottom-right
    "Corridors within autonomous units",     # L4
    "Bedrooms",                              # L5 — centre
    "Living rooms, pantries, and kitchens",  # L6
    "Common use corridors",                  # L7 — top-left
    "Storage rooms",                         # L8
    "Party rooms and game rooms",            # L9 — top-right
]


# ==============================================================================
# Result collector
# ==============================================================================

@dataclass
class IterationRecord:
    slab_id: str
    iteration: int
    thickness_cm: int
    permanent_load: float   # kN/m²
    variable_load: float    # kN/m²
    lx_cm: float
    ly_cm: float
    local: str
    stable: bool            # True = no further increase needed at this step


@dataclass
class PreSizingLog:
    records: list[IterationRecord] = field(default_factory=list)

    def add(self, record: IterationRecord) -> None:
        self.records.append(record)

    def print_table(self) -> None:
        print("\n" + "=" * 100)
        print("SLAB PRE-SIZING — STEP-BY-STEP ITERATIONS")
        print("=" * 100)
        header = f"{'Slab':<6} {'Iter':>4}  {'h (cm)':>7}  {'Lx (cm)':>8}  {'Ly (cm)':>8}  "
        header += f"{'g (kN/m²)':>10}  {'q (kN/m²)':>10}  {'Stable':>7}  {'Local'}"
        print(header)
        print("-" * 100)
        prev_slab = None
        for r in self.records:
            if prev_slab and prev_slab != r.slab_id:
                print()
            stable_str = "YES" if r.stable else "no"
            print(
                f"{r.slab_id:<6} {r.iteration:>4}  {r.thickness_cm:>7}  "
                f"{r.lx_cm:>8.0f}  {r.ly_cm:>8.0f}  "
                f"{r.permanent_load:>10.3f}  {r.variable_load:>10.3f}  "
                f"{stable_str:>7}  {r.local}"
            )
            prev_slab = r.slab_id
        print("=" * 100)

    def export_csv(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "slab_id", "iteration", "thickness_cm",
                "lx_cm", "ly_cm",
                "permanent_load_kNm2", "variable_load_kNm2",
                "stable", "local",
            ])
            for r in self.records:
                writer.writerow([
                    r.slab_id, r.iteration, r.thickness_cm,
                    r.lx_cm, r.ly_cm,
                    r.permanent_load, r.variable_load,
                    r.stable, r.local,
                ])
        print(f"[CSV EXPORTED] {path}")

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("FINAL SLAB THICKNESSES")
        print("=" * 60)
        final: dict[str, IterationRecord] = {}
        for r in self.records:
            final[r.slab_id] = r  # last record per slab = final state
        for slab_id, r in sorted(final.items()):
            total_iters = sum(1 for rec in self.records if rec.slab_id == slab_id)
            print(
                f"  {slab_id}: h = {r.thickness_cm:>2} cm  "
                f"({total_iters} iteration{'s' if total_iters > 1 else ''})  "
                f"[{r.local}]"
            )
        print("=" * 60 + "\n")


# ==============================================================================
# Instrumented pre-sizing (wraps Slab.pre_size to capture each step)
# ==============================================================================

def pre_size_slab_with_log(slab: Slab, log: PreSizingLog) -> bool:
    """Runs the slab's pre-sizing loop while recording every thickness trial."""
    from src.loading.slab_deformation_checker import SlabDeformationChecker
    from src.pavement.slab_edge import Edges

    concrete = Concrete[APP_CONFIG.pavement_concrete]
    original_thickness = slab.thickness

    mock_tensioned_reinforcement_area = 3.57  # FIXME: same placeholder as slab.pre_size()
    mock_effective_depth_discount = 3         # FIXME
    mock_compressed_reinforcement_area = 0.0  # FIXME
    mock_compressed_effective_depth = 0.0     # FIXME

    support_conditions = {edge: slab.edges[edge].support_condition for edge in Edges}
    lx, ly = slab.dimensions

    # Separate permanent load into non-self-weight part and current self-weight so
    # we can recompute self-weight for each thickness trial without drift across passes.
    # base_self_weight must reflect the thickness already embedded in slab.permanent_load
    # (which may have been updated by a prior pass), not always SLAB_MIN_THICKNESS.
    base_self_weight = SuperficialLoads.get_concrete_element_own_weight(slab.thickness / 100)
    base_permanent_load = slab.permanent_load  # includes base_self_weight for current thickness

    def _make_checker(thickness: int) -> SlabDeformationChecker:
        self_weight = SuperficialLoads.get_concrete_element_own_weight(thickness / 100)
        current_permanent_load = base_permanent_load - base_self_weight + self_weight
        return SlabDeformationChecker(
            permanent_load=current_permanent_load,
            variable_load=slab.variable_load,
            usage=slab.local,
            concrete=concrete,
            lx=lx,
            ly=ly,
            support_conditions=support_conditions,
        )

    iteration = 0
    while True:
        current_self_weight = SuperficialLoads.get_concrete_element_own_weight(slab.thickness / 100)
        current_permanent_load = base_permanent_load - base_self_weight + current_self_weight
        if _make_checker(slab.thickness).verify(slab.thickness):
            break
        log.add(IterationRecord(
            slab_id=slab.id,
            iteration=iteration,
            thickness_cm=slab.thickness,
            permanent_load=current_permanent_load,
            variable_load=slab.variable_load,
            lx_cm=lx,
            ly_cm=ly,
            local=slab.local,
            stable=False,
        ))
        iteration += 1
        slab.thickness += 1
        if slab.thickness > SLAB_MAX_THICKNESS:
            raise ValueError(
                f"Slab '{slab.id}' cannot be stabilized; required thickness exceeds 30 cm."
            )

    # Record the passing thickness
    final_self_weight = SuperficialLoads.get_concrete_element_own_weight(slab.thickness / 100)
    final_permanent_load = base_permanent_load - base_self_weight + final_self_weight
    slab.permanent_load = final_permanent_load  # sync slab's load to the final thickness
    log.add(IterationRecord(
        slab_id=slab.id,
        iteration=iteration,
        thickness_cm=slab.thickness,
        permanent_load=final_permanent_load,
        variable_load=slab.variable_load,
        lx_cm=lx,
        ly_cm=ly,
        local=slab.local,
        stable=True,
    ))

    return slab.thickness == original_thickness


# ==============================================================================
# 1. BUILD THE PAVEMENT
# ==============================================================================

def _pillar_index(col: int, row: int) -> int:
    """Converts 0-based (col, row) grid position to a 1-based pillar index."""
    return row * N_COLS + col + 1


def build_pavement() -> tuple[Pavement, list[Slab]]:
    """Builds the 4×4 pillar grid, beams, and 9 slabs."""
    pavement = Pavement()

    # --- Pillars: 4 columns × 4 rows -----------------------------------------
    pillar_grid: list[list[Pillar]] = []
    for row in range(N_ROWS):
        pillar_row: list[Pillar] = []
        for col in range(N_COLS):
            p = Pillar(
                x=PILLAR_X_COORDS[col],
                y=PILLAR_Y_COORDS[row],
                width=PILLAR_DIM,
                depth=PILLAR_DIM,
            )
            pavement.add_pillar(p)
            pillar_row.append(p)
        pillar_grid.append(pillar_row)

    wall = WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )

    # --- Horizontal beams (X-axis): one per row, split per column segment ----
    # Outer rows use outer alignment; inner rows are centered.
    for row in range(N_ROWS):
        if row == 0:
            alignment = Alignment.BOTTOM
        elif row == N_ROWS - 1:
            alignment = Alignment.TOP
        else:
            alignment = Alignment.CENTER

        # One continuous beam spanning all 4 pillars in this row
        row_pillar_ids = [pillar_grid[row][col].id for col in range(N_COLS)]
        reference_id = row_pillar_ids[0]
        pavement.add_beam(
            ContinuousBeam(
                pillar_ids=row_pillar_ids,
                reference_pillar_id=reference_id,
                width=BEAM_WIDTH,
                alignment=alignment,
                wall=wall,
            )
        )

    # --- Vertical beams (Y-axis): one per column, spanning all rows ----------
    for col in range(N_COLS):
        if col == 0:
            alignment = Alignment.LEFT
        elif col == N_COLS - 1:
            alignment = Alignment.RIGHT
        else:
            alignment = Alignment.CENTER

        col_pillar_ids = [pillar_grid[row][col].id for row in range(N_ROWS)]
        reference_id = col_pillar_ids[0]
        pavement.add_beam(
            ContinuousBeam(
                pillar_ids=col_pillar_ids,
                reference_pillar_id=reference_id,
                width=BEAM_WIDTH,
                alignment=alignment,
                wall=wall,
            )
        )

    # --- 9 Slabs: row-major from bottom-left ---------------------------------
    slabs: list[Slab] = []
    slab_index = 0
    for row in range(N_ROWS - 1):
        for col in range(N_COLS - 1):
            local = SLAB_LOCALS[slab_index]
            slab = Slab(
                corner_pillar_ids=(
                    pillar_grid[row][col].id,
                    pillar_grid[row][col + 1].id,
                    pillar_grid[row + 1][col].id,
                    pillar_grid[row + 1][col + 1].id,
                ),
                local=local,
            )
            floor_covering = SuperficialLoads.get_top_finish_weight(
                "Floor coverings of residential", thickness=5.0
            )
            ceiling = SuperficialLoads.get_ceiling_weight("plaster")
            self_weight = SuperficialLoads.get_concrete_element_own_weight(
                SLAB_MIN_THICKNESS / 100
            )
            slab.add_permanent_load(floor_covering + ceiling + self_weight)
            pavement.add_slab(slab)
            slabs.append(slab)
            slab_index += 1

    return pavement, slabs


# ==============================================================================
# 2. PRE-SIZE ALL SLABS WITH LOGGING
# ==============================================================================

def pre_size_all_slabs(slabs: list[Slab], log: PreSizingLog) -> None:
    """Iterates until all slabs reach a stable thickness (mirrors Pavement.pre_size_slabs)."""
    changed = [None] * len(slabs)
    while False in changed or None in changed:
        for i, slab in enumerate(slabs):
            # Reset thickness to minimum before each global pass so the log
            # captures iterations from the actual starting point each round.
            changed[i] = pre_size_slab_with_log(slab, log)


# ==============================================================================
# 3. MAIN
# ==============================================================================

def main() -> None:
    pavement, slabs = build_pavement()
    pavement.validate()
    pavement.pre_size_beams()
    pavement.load_beam_spans()

    log = PreSizingLog()
    pre_size_all_slabs(slabs, log)

    pavement.unload_slabs_on_beams()

    log.print_table()
    log.print_summary()

    today = datetime.now().strftime("%b-%d").lower()
    csv_path = f"results/{today}/slab_pre_sizing_iterations.csv"
    log.export_csv(csv_path)


if __name__ == "__main__":
    main()
