"""Read the design's materials from the engine settings."""

from pavement_ui.core.results.materials import MaterialsInfo
from src.config import APP_CONFIG
from src.pavement_elements.slab import Slab
from src.structural_elements.rectangular_beam import RectangularBeam

_MPA_PER_KN_CM2 = 10.0


def read_materials() -> MaterialsInfo:
    """Return the pavement's concrete and steel, with strengths in MPa

    Must run while APP_CONFIG holds the design settings.
    """
    concrete = APP_CONFIG.pavement_concrete
    steel = APP_CONFIG.pavement_steel
    return MaterialsInfo(
        concrete=concrete.name,
        steel=steel.name,
        fck_mpa=float(concrete.value),
        fcd_mpa=concrete.fcd * _MPA_PER_KN_CM2,
        fctm_mpa=concrete.fct_m * _MPA_PER_KN_CM2,
        fctd_mpa=concrete.fctd * _MPA_PER_KN_CM2,
        ecs_mpa=concrete.ecs,
        fyk_mpa=steel.value * _MPA_PER_KN_CM2,
        fyd_mpa=steel.fyd * _MPA_PER_KN_CM2,
        fywd_mpa=steel.fywd * _MPA_PER_KN_CM2,
        beam_cover_cm=RectangularBeam.nominal_covering,
        slab_cover_cm=Slab.nominal_covering,
    )
