"""Read the skin reinforcement of a span."""

from pavement_ui.core.results.beam_design import SkinDesign
from src.reinforcement.skin_reinforcement import SkinReinforcement


def read_skin_design(skin: SkinReinforcement | None) -> SkinDesign | None:
    """Return the span's skin bars and the area they were chosen for; None when not required"""
    if skin is None or skin.layout is None:
        return None
    layout = skin.layout
    return SkinDesign(
        required_area_cm2=skin.required_area,
        provided_area_cm2=layout.area_per_face,
        diameter_mm=layout.diameter_mm,
        bars_per_face=layout.bars_per_face,
        spacing_cm=layout.spacing,
        band_start_cm=layout.band_start,
        band_end_cm=layout.band_end,
    )
