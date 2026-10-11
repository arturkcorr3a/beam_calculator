"""Labels of elements and design points: "Vão 1 (M+)", "P1 – P2 – P3", "600 × 400"."""

from collections.abc import Sequence

from pavement_ui.core.model.pavement_records import ElementCounts
from pavement_ui.core.results.beam_result import DesignPoint, PointKind
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.strings import formatting as s


def fmt_point_label(point: DesignPoint) -> str:
    """Label a design point, e.g. "Vão 1 (M+)" or "Apoio P2 (M−)" """
    sign = s.MOMENT_POSITIVE if point.bottom_tensioned else s.MOMENT_NEGATIVE
    template = s.POINT_SPAN if point.kind is PointKind.SPAN else s.POINT_SUPPORT
    return template.format(ref=point.ref, sign=sign)


def fmt_pillar_chain(ids: Sequence[str]) -> str:
    """Join pillar IDs, e.g. ("P1", "P2", "P3") → "P1 – P2 – P3" """
    return s.CHAIN_JOIN.join(ids)


def fmt_dims_cm(lx_cm: float, ly_cm: float) -> str:
    """Format slab dimensions (cm), e.g. "600 × 400" """
    return s.DIMS.format(lx=fmt_number(lx_cm, 0), ly=fmt_number(ly_cm, 0))


def fmt_count(n: int, singular: str, plural: str) -> str:
    """Format a count with the right noun, e.g. "1 viga", "5 vigas" """
    return f"{n} {singular if n == 1 else plural}"


def fmt_counts(counts: ElementCounts) -> str:
    """Summarize the elements, e.g. "6 pilares · 5 vigas · 2 lajes" """
    return s.COUNT_JOIN.join(
        (
            fmt_count(counts.pillars, s.PILLAR_SINGULAR, s.PILLAR_PLURAL),
            fmt_count(counts.beams, s.BEAM_SINGULAR, s.BEAM_PLURAL),
            fmt_count(counts.slabs, s.SLAB_SINGULAR, s.SLAB_PLURAL),
        )
    )
