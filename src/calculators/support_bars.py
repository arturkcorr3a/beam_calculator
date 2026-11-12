"""Carry part of each span's positive reinforcement to its supports."""

from collections.abc import Sequence
from dataclasses import dataclass

from src.logger import log_operation, log_property
from src.reinforcement.reinforcement import END_SUPPORT_TOLERANCE, Reinforcement

LARGE_NEGATIVE_SUPPORT_RATIO = 0.5  # |M_apoio| / M_vão above which 1/4 applies
SHARE_SMALL_SUPPORT_MOMENT = 1 / 3
SHARE_LARGE_NEGATIVE_SUPPORT_MOMENT = 1 / 4


@dataclass(frozen=True, slots=True)
class SpanRange:
    """A span's extent along the beam and its supports

    Attributes:
        start: Theoretical start support position (cm).
        end: Theoretical end support position (cm).
        start_support_index: Index of the start support in ``beam.supports``.
        end_support_index: Index of the end support in ``beam.supports``.
    """

    start: float
    end: float
    start_support_index: int
    end_support_index: int


def support_area_share(support_moment: float, span_moment: float) -> float:
    """Return the share of the span's area the bars carried to a support must reach

    One quarter when the support moment is negative and its absolute value exceeds half the span moment; one third otherwise (a positive support moment keeps one third, the stricter share).

    Args:
        support_moment: Characteristic moment on the support (kN.m), signed.
        span_moment: Characteristic maximum positive moment of the span (kN.m).

    References:
        ABNT NBR 6118:2026 — Section 18.3.2.4-c
    """
    is_large_negative = (
        support_moment < 0
        and abs(support_moment) > LARGE_NEGATIVE_SUPPORT_RATIO * span_moment
    )
    if is_large_negative:
        return SHARE_LARGE_NEGATIVE_SUPPORT_MOMENT
    return SHARE_SMALL_SUPPORT_MOMENT


def carry_span_bars_to_supports(
    reinforcements: Sequence[Reinforcement], spans: Sequence[SpanRange]
) -> None:
    """Extend each span's bottom layers into its supports until they carry the required share

    For each span, the bottom reinforcement of its greatest positive moment is checked at both supports. The layers already anchored inside a support count towards the share; while the share is not met, the next layer that does not reach the support (layer 0 first) is extended into it.

    Args:
        reinforcements: The beam's chosen reinforcements, of every interest point.
        spans: The beam's spans, left to right.

    Raises:
        ValueError: If a span's layers cannot reach the share even when all are extended, or propagated from the anchorage inside a support.

    References:
        ABNT NBR 6118:2026 — Sections 18.3.2.4-c and 18.3.2.4.1
    """
    for span in spans:
        reinforcement = _span_reinforcement(reinforcements, span)
        if reinforcement is None:
            continue
        _carry_to_support(reinforcement, span.start_support_index, left=True)
        _carry_to_support(reinforcement, span.end_support_index, left=False)


def _span_reinforcement(
    reinforcements: Sequence[Reinforcement], span: SpanRange
) -> Reinforcement | None:
    """Return the span's positive bottom reinforcement with the greatest span moment, or None"""
    candidates = [
        reinforcement
        for reinforcement in reinforcements
        if reinforcement.is_tensioned
        and reinforcement.is_bottom_reinforcement
        and reinforcement.span_moment is not None
        and span.start - END_SUPPORT_TOLERANCE
        <= reinforcement.center_position
        <= span.end + END_SUPPORT_TOLERANCE
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.span_moment or 0.0)


def _carry_to_support(
    reinforcement: Reinforcement, support_index: int, left: bool
) -> None:
    """Extend the reinforcement's layers into one support, in order, until the share is met

    Raises:
        ValueError: If the required area is not set, or the share is not met even with every layer extended.
    """
    if reinforcement.required_area is None or reinforcement.span_moment is None:
        raise ValueError(
            f"Reinforcement at {reinforcement.center_position:.2f} cm has no required area or span moment."
        )
    support_moment = reinforcement.support_moment(support_index)  # kN.m
    share = support_area_share(support_moment, reinforcement.span_moment)
    required = share * reinforcement.required_area  # cm²

    layer_indices = [
        layer.layer_index for layer in reinforcement.chosen_bars if layer.bars
    ]
    reaching = {
        index: reinforcement.layer_reaches_support(index, support_index, left)
        for index in layer_indices
    }
    carried = sum(
        reinforcement.chosen_bars[index].area
        for index in layer_indices
        if reaching[index]
    )  # cm²
    log_property(
        f"Support {support_index} (M_apoio = {support_moment:.2f} kN.m, M_vão = {reinforcement.span_moment:.2f} kN.m): carried A_s = {carried:.3f} cm², required {share:.3f} A_s,vão = {required:.3f} cm²"
    )

    for index in layer_indices:
        if carried >= required:
            break
        if reaching[index]:
            continue
        log_operation(
            f"Extending layer {index} of the reinforcement at {reinforcement.center_position:.2f} cm into support {support_index} (NBR 6118 - 18.3.2.4-c)."
        )
        reinforcement.extend_layer_to_support(index, support_index, left)
        carried += reinforcement.chosen_bars[index].area

    if carried < required:
        error_message = f"Bars carried to support {support_index} ({carried:.3f} cm²) are below {share:.3f} of the span's area ({required:.3f} cm²)."
        log_operation(error_message)
        raise ValueError(error_message)
