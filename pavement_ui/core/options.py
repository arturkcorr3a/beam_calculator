"""Choices offered by the engine for every option field (keys only, no labels).

Read once from the engine by the adapters; the presentation maps each key to
its pt-BR label. Nothing here is a fixed list of the UI (docs/UI_SPEC.md §6.4).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThicknessOption:
    """A nominal wall thickness and the coatings tabulated for it

    Attributes:
        nominal_cm: Nominal thickness (cm).
        coatings_cm: Coating thicknesses per face available for it (cm).
    """

    nominal_cm: float
    coatings_cm: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MasonryOption:
    """A masonry type of NBR 6120 Table 2

    Attributes:
        key: Engine description of the masonry type.
        structural: Whether it is in the structural list.
        thicknesses: Tabulated nominal thicknesses.
    """

    key: str
    structural: bool
    thicknesses: tuple[ThicknessOption, ...]


@dataclass(frozen=True, slots=True)
class EngineOptions:
    """Keys of every option the engine accepts, in display order

    Attributes:
        usages_by_category: (category key, usage keys) pairs of NBR 6120 Table 10;
            some categories have no usages.
        log_dir: Folder where the engine writes the calculation memorial.
    """

    concrete_classes: tuple[str, ...] = ()
    steels: tuple[str, ...] = ()
    aggregates: tuple[str, ...] = ()
    exposure_classes: tuple[str, ...] = ()
    building_categories: tuple[str, ...] = ()
    alignments: tuple[str, ...] = ()
    log_levels: tuple[str, ...] = ()
    log_outputs: tuple[str, ...] = ()
    masonry: tuple[MasonryOption, ...] = ()
    usages_by_category: tuple[tuple[str, tuple[str, ...]], ...] = ()
    log_dir: str = ""

    def masonry_for(self, structural: bool) -> tuple[MasonryOption, ...]:
        """Return the masonry types of the structural or the non-bearing list"""
        return tuple(m for m in self.masonry if m.structural == structural)

    def usages_for(self, category_key: str) -> tuple[str, ...]:
        """Return the slab usages of a building category (empty if it has none)"""
        return dict(self.usages_by_category).get(category_key, ())
