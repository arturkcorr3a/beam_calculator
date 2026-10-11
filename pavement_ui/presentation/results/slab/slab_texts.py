"""Formatted texts shared by the slab detail groups."""

from pavement_ui.core.results.slab_result import EdgeSupport, SlabResult
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import results as s


def slab_type(result: SlabResult) -> str:
    """ "Armada em duas direções" or "Armada em uma direção" """
    return label(OptionKind.SLAB_TYPE, "two_way" if result.two_way else "one_way")


def slab_type_with_ratio(result: SlabResult) -> str:
    """The type with the effective-span ratio, e.g. "… (600 / 400 = 1,5 ≤ 2)" """
    long, short = (
        max(result.lx_ef_cm, result.ly_ef_cm),
        min(result.lx_ef_cm, result.ly_ef_cm),
    )
    ratio = long / short
    return s.TYPE_WITH_RATIO.format(
        type=slab_type(result),
        long=fmt_number(long, 0),
        short=fmt_number(short, 0),
        ratio=fmt_number(ratio, 2),
        comparison="≤" if result.two_way else ">",
        limit=fmt_number(result.one_way_ratio_limit, 0),
    )


def condition(edge: EdgeSupport) -> str:
    """ "Engastada" or "Apoiada" """
    return label(OptionKind.SUPPORT_CONDITION, "fixed" if edge.fixed else "pinned")


def condition_with_neighbor(edge: EdgeSupport) -> str:
    """The condition; a fixed edge also names the slab it is continuous with"""
    if edge.fixed and edge.neighbor_slab_id is not None:
        return s.FIXED_WITH_NEIGHBOR.format(
            condition=condition(edge), neighbor=edge.neighbor_slab_id
        )
    return condition(edge)


def cm(value: float, decimals: int = 0) -> str:
    return s.CM_VALUE.format(value=fmt_number(value, decimals))
