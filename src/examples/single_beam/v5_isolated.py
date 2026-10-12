"""
Beam V5 (P7-P5-P2) from saved/saved.yaml, dimensioned in isolation: the slab
reactions are given directly instead of being computed by the pavement.
"""

from src.loading.combination_factors import almost_permanent_reduction_factor
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.persistency import load_pavement

PATH = "saved/saved.yaml"
BEAM_PILLAR_IDS = {"P7", "P5", "P2"}

# Slab reactions per span (kN/m): (permanent, variable)
SLAB_LOADS: dict[tuple[str, str], tuple[float, float]] = {
    ("P7", "P5"): (8.69, 5.14),
    ("P5", "P2"): (11.47, 7.22),
}
SLAB_LOCAL = "Bedrooms"  # sets psi_2 of the variable loads


def find_beam(beams: dict[str, ContinuousBeam]) -> ContinuousBeam:
    """Return the beam supported exactly by BEAM_PILLAR_IDS"""
    for beam in beams.values():
        if set(beam.pillar_ids) == BEAM_PILLAR_IDS:
            return beam
    raise ValueError(f"No beam over pillars {sorted(BEAM_PILLAR_IDS)} in {PATH}")


def main() -> None:
    pavement = load_pavement(PATH)  # also applies the saved config to APP_CONFIG
    pillars = pavement.pillars
    beam = find_beam(pavement.beams)

    beam.resolve_and_validate(pillars)
    beam.pre_size(pillars)
    beam.load_spans()  # self-weight and wall

    psi_2 = almost_permanent_reduction_factor(SLAB_LOCAL)
    for span in beam.spans:
        permanent, variable = SLAB_LOADS[(span.start_pillar_id, span.end_pillar_id)]
        span.add_load(permanent, permanent=True)
        span.add_load(variable, permanent=False, psi_2=psi_2)

    breakpoint()
    beam.dimension(pillars)
    print(beam.report(pillars))


if __name__ == "__main__":
    main()
