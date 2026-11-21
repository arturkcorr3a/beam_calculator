"""Read every option the engine accepts into EngineOptions."""

from pavement_ui.core.engine.keys import to_key
from pavement_ui.core.options import EngineOptions, MasonryOption, ThicknessOption
from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.data.nbr6120_2019.table_2.data import TABLE_2
from src.data.nbr6120_2019.table_2.model import MasonryType, Thickness
from src.data.nbr6120_2019.table_10.data import TABLE_10
from src.logger import LogLevel, default_logs_dir
from src.pavement_elements.geometry_utils import Alignment
from src.properties.concrete import Concrete
from src.properties.steel import Steel

# Combo order of the beam form: center works for both axes
_ALIGNMENT_ORDER = (
    Alignment.CENTER,
    Alignment.TOP,
    Alignment.BOTTOM,
    Alignment.LEFT,
    Alignment.RIGHT,
)
_COATINGS_CM = (0, 1, 2)


def _thickness_option(thickness: Thickness) -> ThicknessOption:
    weights = (thickness.zero_cm, thickness.one_cm, thickness.two_cm)
    coatings = tuple(
        c for c, w in zip(_COATINGS_CM, weights, strict=True) if w is not None
    )
    return ThicknessOption(thickness.nominal_cm, coatings)


def _masonry_option(masonry: MasonryType) -> MasonryOption:
    thicknesses = tuple(_thickness_option(t) for t in masonry.thicknesses)
    return MasonryOption(masonry.type_description, thicknesses)


def _masonry() -> tuple[MasonryOption, ...]:
    return tuple(_masonry_option(m) for m in TABLE_2.masonry)


def _usages_by_category() -> tuple[tuple[str, tuple[str, ...]], ...]:
    pairs: list[tuple[str, tuple[str, ...]]] = []
    for category in OccupancyCategory:
        locations = TABLE_10.find_category(category.value).locations
        pairs.append((to_key(category), tuple(loc.description for loc in locations)))
    return tuple(pairs)


def read_options() -> EngineOptions:
    """Read the engine's enums and NBR 6120 tables (Tables 2 and 10)

    Returns:
        Every option key, in display order.
    """
    return EngineOptions(
        concrete_classes=tuple(to_key(c) for c in Concrete),
        steels=tuple(to_key(s) for s in Steel),
        aggregates=tuple(to_key(a) for a in Aggregate),
        exposure_classes=tuple(to_key(e) for e in ExposureClass),
        building_categories=tuple(to_key(c) for c in OccupancyCategory),
        alignments=tuple(to_key(a) for a in _ALIGNMENT_ORDER),
        log_levels=tuple(to_key(level) for level in LogLevel),
        masonry=_masonry(),
        usages_by_category=_usages_by_category(),
        log_dir=str(default_logs_dir()),
    )
