# type: ignore

# cSpell:disable

"""
Manual usage example: modelling and dimensioning a single-panel pavement.

Geometry (all coordinates/sections in cm):

    P3 ---------- V2 (TOP) ---------- P4
    |                                  |
    |                                  |
   V3                                 V4
  (LEFT)            L1 (slab)        (RIGHT)
    |                                  |
    |                                  |
    P1 -------- V1 (BOTTOM) --------- P2

- 4 pillars, each with a *different* cross-section.
- 4 continuous beams forming the rectangular perimeter.
- Every beam is OUTER-aligned: the top beam is flush with the pillars' top
  faces, the bottom beam with the bottom faces, the left beam with the left
  faces and the right beam with the right faces.
- 1 slab (L1) spanning the four pillars.
- Residential loads (NBR 6120): bedroom live load + floor covering, ceiling
  plaster and slab self-weight as permanent load.

Note on outer alignment
------------------------
An outer-aligned beam anchors its width band to *one* reference pillar's outer
face. For that band to be supported by both pillars along the edge, the two
pillars sharing an edge must present the same face coordinate on the
perpendicular axis. With the pillars sitting on the rectangle corners this means
pillars on the same horizontal edge share a depth, and pillars on the same
vertical edge share a width. The four sections below still end up all-distinct:

    P1 (20 x 25)   P2 (30 x 25)
    P3 (20 x 35)   P4 (30 x 35)
"""

from __future__ import annotations

from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")  # headless-safe; the figure is written to disk
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment, Axis
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab


# ==============================================================================
# 1. BUILD THE PAVEMENT
# ==============================================================================
def build_pavement() -> Pavement:
    """Assembles the 4-pillar / 4-beam / 1-slab residential pavement."""
    # --- Pillars (x, y, width, depth) — all four sections distinct -----------
    bottom_left = Pillar(x=0, y=0, width=20, depth=25)
    bottom_right = Pillar(x=500, y=0, width=30, depth=25)
    top_left = Pillar(x=0, y=400, width=20, depth=35)
    top_right = Pillar(x=500, y=400, width=30, depth=35)
    pillars = [bottom_left, bottom_right, top_left, top_right]

    pavement = Pavement()
    for pillar in pillars:
        pavement.add_pillar(pillar)

    # --- Perimeter walls sitting on the beams (non-structural masonry) --------
    wall = WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,  # cm
        coating_thickness=1,  # cm per face
    )

    # --- Beams: rectangular perimeter, each outer-aligned --------------------
    beam_width = 16  # cm — must fit inside every pillar it rests on
    beam_specs = [
        # pillar pair,                        reference,           alignment
        ([bottom_left.id, bottom_right.id], bottom_left.id, Alignment.BOTTOM),
        ([top_left.id, top_right.id], top_left.id, Alignment.TOP),
        ([bottom_left.id, top_left.id], bottom_left.id, Alignment.LEFT),
        ([bottom_right.id, top_right.id], bottom_right.id, Alignment.RIGHT),
    ]
    for pillar_ids, reference_id, alignment in beam_specs:
        pavement.add_beam(
            ContinuousBeam(
                pillar_ids=pillar_ids,
                reference_pillar_id=reference_id,
                width=beam_width,
                alignment=alignment,
                wall=wall,
            )
        )

    # --- Slab spanning the four corner pillars -------------------------------
    slab = Slab(
        corner_pillar_ids=(
            bottom_left.id,
            bottom_right.id,
            top_left.id,
            top_right.id,
        ),
        local="Bedrooms",  # residential usage
    )

    # Residential permanent load (NBR 6120): finish + ceiling + self-weight ---
    floor_covering = SuperficialLoads.get_top_finish_weight(
        "Floor coverings of residential", thickness=5.0
    )  # kN/m²
    ceiling = SuperficialLoads.get_ceiling_weight("plaster")  # kN/m²
    self_weight = SuperficialLoads.get_concrete_element_own_weight(
        slab.thickness / 100  # cm -> m
    )  # kN/m²
    slab.add_permanent_load(floor_covering + ceiling + self_weight)

    pavement.add_slab(slab)
    return pavement


# ==============================================================================
# 2. PLOT THE DESIGNED PAVEMENT
# ==============================================================================
def plot_pavement(
    pavement: Pavement, output_path: str = "results/pavement_layout.png"
) -> str:
    """Draws pillars, perimeter beams and the slab, and annotates dimensions.

    Returns the path of the written figure.
    """
    fig, ax = plt.subplots(figsize=(9, 8))

    # --- Slab (drawn first so it sits behind the structure) ------------------
    for slab in pavement.slabs.values():
        # Slab extent = perimeter beam centerlines
        x_left = min(b.centerline for b in pavement.beams.values() if b.axis == Axis.Y)
        x_right = max(b.centerline for b in pavement.beams.values() if b.axis == Axis.Y)
        y_bottom = min(
            b.centerline for b in pavement.beams.values() if b.axis == Axis.X
        )
        y_top = max(b.centerline for b in pavement.beams.values() if b.axis == Axis.X)
        ax.add_patch(
            Rectangle(
                (x_left, y_bottom),
                x_right - x_left,
                y_top - y_bottom,
                facecolor="#d9e8f5",
                edgecolor="none",
                zorder=1,
            )
        )
        ax.text(
            (x_left + x_right) / 2,
            (y_bottom + y_top) / 2,
            f"{slab.id}\nh = {slab.thickness:.0f} cm\n"
            f"g = {slab.permanent_load:.2f} kN/m²\n"
            f"q = {slab.variable_load:.2f} kN/m²",
            ha="center",
            va="center",
            fontsize=10,
            zorder=5,
        )

    # --- Beams (perimeter), drawn along their centerline band ----------------
    for beam in pavement.beams.values():
        half = beam.width / 2
        if beam.axis == Axis.X:  # horizontal beam
            pillars = [pavement.pillars[pid] for pid in beam.pillar_ids]
            x0 = min(p.x for p in pillars)
            x1 = max(p.x for p in pillars)
            ax.add_patch(
                Rectangle(
                    (x0, beam.centerline - half),
                    x1 - x0,
                    beam.width,
                    facecolor="#f4b183",
                    edgecolor="#843c0c",
                    linewidth=1.2,
                    zorder=3,
                )
            )
            ax.text(
                (x0 + x1) / 2,
                beam.centerline,
                f"{beam.id} ({beam.width}×{beam.height})",
                ha="center",
                va="center",
                fontsize=8,
                zorder=6,
            )
        else:  # vertical beam
            pillars = [pavement.pillars[pid] for pid in beam.pillar_ids]
            y0 = min(p.y for p in pillars)
            y1 = max(p.y for p in pillars)
            ax.add_patch(
                Rectangle(
                    (beam.centerline - half, y0),
                    beam.width,
                    y1 - y0,
                    facecolor="#f4b183",
                    edgecolor="#843c0c",
                    linewidth=1.2,
                    zorder=3,
                )
            )
            ax.text(
                beam.centerline,
                (y0 + y1) / 2,
                f"{beam.id} ({beam.width}×{beam.height})",
                ha="center",
                va="center",
                rotation=90,
                fontsize=8,
                zorder=6,
            )

    # --- Pillars -------------------------------------------------------------
    for pillar in pavement.pillars.values():
        x_lo, _ = pillar.get_x_range()
        y_lo, _ = pillar.get_y_range()
        ax.add_patch(
            Rectangle(
                (x_lo, y_lo),
                pillar.width,
                pillar.depth,
                facecolor="#808080",
                edgecolor="black",
                linewidth=1.5,
                zorder=4,
            )
        )
        ax.text(
            pillar.x,
            pillar.y,
            f"{pillar.id}\n{pillar.width}×{pillar.depth}",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
            fontweight="bold",
            zorder=7,
        )

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.15)
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("y (cm)")
    ax.set_title("Designed pavement — outer-aligned perimeter beams")
    ax.grid(True, linestyle=":", alpha=0.4)

    import os

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=130)
    plt.close(fig)
    return output_path


# ==============================================================================
# 3. DISPLAY THE DIMENSIONING PARAMETERS
# ==============================================================================
def print_parameters(pavement: Pavement) -> None:
    """Prints a compact table of the resolved dimensioning parameters."""
    print("\n" + "=" * 68)
    print("PAVEMENT DIMENSIONING PARAMETERS")
    print("=" * 68)

    print("\nPillars (id: width × depth, position):")
    for pillar in pavement.pillars.values():
        print(
            f"  {pillar.id}: {pillar.width:.0f} × {pillar.depth:.0f} cm"
            f"   @ (x={pillar.x:.0f}, y={pillar.y:.0f})"
        )

    print("\nSlabs:")
    for slab in pavement.slabs.values():
        lx, ly = slab.dimensions
        print(
            f"  {slab.id}: {lx:.0f} × {ly:.0f} cm   thickness = {slab.thickness:.0f} cm"
        )
        print(
            f"       permanent g = {slab.permanent_load:.2f} kN/m²"
            f"   |   variable q = {slab.variable_load:.2f} kN/m²"
        )

    print("\nBeams (pre-sized, with resolved span loads):")
    for beam in pavement.beams.values():
        print(
            f"  {beam.id} [{beam.axis.value}-axis, {beam.alignment.value}]: "
            f"{beam.width:.0f} × {beam.height:.0f} cm   "
            f"centerline = {beam.centerline:.1f} cm"
        )
        for i, span in enumerate(beam.spans, start=1):
            print(
                f"       span {i}: g = {span.permanent_load:.2f} kN/m"
                f"   |   q = {span.variable_load:.2f} kN/m"
            )
    print("=" * 68 + "\n")


# ==============================================================================
# 4. MAIN
# ==============================================================================
def main() -> None:
    pavement = build_pavement()

    # Resolve geometry and derive spans / centerlines.
    pavement.validate()

    # Pre-dimension beams and propagate loads down to the beam spans.
    # NOTE: Pavement.resolve() is not used here because Slab.pre_size() is still
    # a placeholder (raises NotImplementedError). We run the working steps
    # explicitly instead.
    pavement.pre_size_beams()
    pavement.load_beam_spans()
    pavement.unload_slabs_on_beams()

    # Show the resolved parameters and draw the layout.
    print_parameters(pavement)
    today = datetime.now(tz=timezone.utc).strftime("%b-%d").lower()
    path = f"results/{today}/pavement_layout.png"
    figure_path = plot_pavement(pavement, path)
    print(f"[FIGURE SAVED] {figure_path}")

    # Final beam dimensioning + report export.
    # NOTE: the slab influence-area split is still a simplified model
    # (proportional to side length; see Slab.resolve_influence_areas), but the
    # loads it produces are now in consistent units, so the rebar/stirrup
    # solver runs. We still guard it so the geometry/parameters above are shown
    # even if a particular beam cannot be solved.
    try:
        pavement.dimension_beams()
        pavement.print_beam_reports()
    except Exception as exc:  # noqa: BLE001 — example-level guard
        print(
            "[DIMENSIONING SKIPPED] Beam reinforcement could not be computed:\n"
            f"    {exc}"
        )


if __name__ == "__main__":
    main()
