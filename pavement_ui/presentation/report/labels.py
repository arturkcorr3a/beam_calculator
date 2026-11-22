"""Labels shared by the report sections."""

from pavement_ui.core.results.beam_result import BeamResult, SpanResult
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.text.strings import report as s


def span_name(span: SpanResult) -> str:
    """Name a span with its supports, e.g. "1 (P1 – P2)" """
    return s.SPAN_NAME.format(
        index=span.index, start=span.start_label, end=span.end_label
    )


def height_raise_lines(result: BeamResult) -> list[str]:
    """One sentence per height raise of the beam, e.g. "Altura elevada de 40 para 45 cm: …" """
    return [
        s.HEIGHT_RAISED.format(
            from_=fmt_length_cm(raise_.from_cm),
            to=fmt_length_cm(raise_.to_cm),
            reason=s.HEIGHT_RAISE_REASONS.get(raise_.reason, raise_.reason),
        )
        for raise_ in result.height_raises
    ]
