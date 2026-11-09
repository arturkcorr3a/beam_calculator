"""Labels shared by the report sections."""

from pavement_ui.core.results.beam_result import SpanResult
from pavement_ui.presentation.text.strings import report as s


def span_name(span: SpanResult) -> str:
    """Name a span with its supports, e.g. "1 (P1 – P2)" """
    return s.SPAN_NAME.format(
        index=span.index, start=span.start_label, end=span.end_label
    )
