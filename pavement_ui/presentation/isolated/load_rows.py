"""The g and q of each listed load and the text of its row in the loads table."""

from collections.abc import Sequence
from dataclasses import dataclass

from pavement_ui.core.model.isolated_beam_input import (
    CustomLoad,
    IsolatedLoadInput,
    OwnWeightLoad,
    WallLoad,
)
from pavement_ui.core.ports import IsolatedBeamEngine
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.text.option_labels import OptionKind, short_label
from pavement_ui.presentation.text.strings import isolated as s


@dataclass(frozen=True, slots=True)
class LoadValues:
    """A load's intensity as the engine computes it

    Attributes:
        g_kn_m: Permanent part (kN/m).
        q_kn_m: Variable part (kN/m).
    """

    g_kn_m: float
    q_kn_m: float


def load_values(
    load: IsolatedLoadInput,
    engine: IsolatedBeamEngine,
    width_cm: float,
    height_cm: float,
) -> LoadValues:
    """Return the load's g and q; a wall missing from the catalogue counts as zero"""
    match load:
        case OwnWeightLoad():
            return LoadValues(engine.self_weight_kn_m(width_cm, height_cm), 0.0)
        case WallLoad():
            try:
                return LoadValues(engine.wall_load_kn_m(load.wall, load.height_m), 0.0)
            except KeyError, ValueError:
                return LoadValues(0.0, 0.0)
        case CustomLoad(variable=True):
            return LoadValues(0.0, load.value_kn_m)
        case CustomLoad():
            return LoadValues(load.value_kn_m, 0.0)


def description(load: IsolatedLoadInput) -> str:
    match load:
        case OwnWeightLoad():
            return s.LOAD_OWN_WEIGHT
        case WallLoad():
            return s.LOAD_WALL.format(
                masonry=short_label(OptionKind.MASONRY, load.wall.masonry_key),
                thickness=fmt_length_cm(load.wall.nominal_thickness_cm),
                height=fmt_number(load.height_m, 2),
            )
        case CustomLoad():
            return load.label


def scope(load: IsolatedLoadInput) -> str:
    index = load.span_index
    return s.ALL_SPANS if index is None else s.SPAN_NAME.format(n=index + 1)


def span_totals(
    loads: Sequence[IsolatedLoadInput],
    values: Sequence[LoadValues],
    span_count: int,
) -> list[LoadValues]:
    """Add up the loads acting on each span, for the scheme"""
    totals = [LoadValues(0.0, 0.0) for _ in range(span_count)]
    for load, value in zip(loads, values, strict=True):
        spans = range(span_count) if load.span_index is None else [load.span_index]
        for index in spans:
            if index < span_count:
                total = totals[index]
                totals[index] = LoadValues(
                    total.g_kn_m + value.g_kn_m, total.q_kn_m + value.q_kn_m
                )
    return totals
