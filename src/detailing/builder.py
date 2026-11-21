from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, cast

from src.detailing.clear_span import ClearSpan
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.reinforcement.clamps import Clamps
from src.reinforcement.layer import Layer
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrups import Stirrups, StirrupZone
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam
    from src.pavement_elements.slab import Slab

_MM_PER_CM = 10.0
_ZONE_TOLERANCE = 1e-3  # cm, zones shorter than this after clipping are dropped


def build_detailing_beam(beam: ContinuousBeam) -> DetailingBeam:
    """Copy a dimensioned beam's bars, clamps, stirrups and skin bars into a new detailing beam

    The design objects are only read: every bar run, clamp set, stirrup set and skin bar set is a new object. Each layer becomes one bar run per diameter, with the layer's own lengths and hooks. Error messages do not name the beam; ``ContinuousBeam.detail`` prefixes them.

    Raises:
        ValueError: If the beam has not been dimensioned (no analysis or no stirrups on a span), a stirrup has no diameter or spacing, or a reinforcement has no required or provided area.
    """
    structural_beam = _structural_beam(beam)
    supports = tuple(structural_beam.supports)
    if len(supports) != len(beam.spans) + 1:
        raise ValueError(
            f"{len(supports)} supports for {len(beam.spans)} spans; can't detail the bars."
        )

    detailing = DetailingBeam(
        beam_id=beam.id,
        width=structural_beam.width,
        height=structural_beam.height,
        nominal_covering=RectangularBeam.nominal_covering,
        steel=structural_beam.steel,
        supports=supports,
        analysis=beam.analysis,
    )
    for reinforcement in beam.reinforcement:
        detailing.bars += _bars(reinforcement, structural_beam.height)
        detailing.clamps += _clamps(reinforcement)
    detailing.stirrups = _stirrups(beam, structural_beam, supports)
    detailing.clear_spans = _clear_spans(beam, structural_beam.height, supports)
    detailing.skin_bars = _skin_bars(beam, supports)
    return detailing


def _structural_beam(beam: ContinuousBeam) -> RectangularBeam:
    """Return the section the beam was dimensioned with

    Raises:
        ValueError: If the beam has no analysis, no spans, or a span without stirrups.
    """
    is_dimensioned = (
        beam.analysis is not None
        and bool(beam.spans)
        and all(hasattr(span, "stirrups") for span in beam.spans)
    )
    if not is_dimensioned:
        raise ValueError("The beam has not been dimensioned; can't detail its bars.")
    return beam.spans[0].stirrups.beam


def _bars(reinforcement: Reinforcement, height: float) -> list[DetailedBar]:
    """Build one bar run per diameter of each non-empty layer, layer by layer

    A reinforcement stacked on another one numbers its layers after its base's.

    Args:
        height: Section height h (cm), for the bond zone.
    """
    center = reinforcement.center_position  # cm
    area_ratio = _area_ratio(reinforcement)
    bars: list[DetailedBar] = []
    for position, layer in enumerate(reinforcement.chosen_bars):
        if not layer.bars:
            continue
        good_adherence = layer.has_good_adherence(height)
        for rebar, quantity in _runs(layer):
            bars.append(
                DetailedBar(
                    diameter_mm=rebar.diameter_mm,
                    steel=rebar.steel,
                    quantity=quantity,
                    is_bottom=reinforcement.is_bottom_reinforcement,
                    is_tensioned=reinforcement.is_tensioned,
                    layer_index=reinforcement.first_layer_index + position,
                    y=_bar_height(reinforcement, position, rebar),
                    start=center - rebar.left_length,
                    end=center + rebar.right_length,
                    left_hook=rebar.hook_geometry(left=True),
                    right_hook=rebar.hook_geometry(left=False),
                    left_hook_length=rebar.left_hook_length,
                    right_hook_length=rebar.right_hook_length,
                    source_positions=(center,),
                    good_adherence=good_adherence,
                    area_ratio=area_ratio,
                )
            )
    return bars


def _runs(layer: Layer) -> list[tuple[Rebar, int]]:
    """Group a layer's bars by diameter, largest first, with each diameter's count"""
    by_diameter: dict[float, list[Rebar]] = {}
    for bar in layer.bars:
        by_diameter.setdefault(bar.diameter_mm, []).append(bar)
    return [
        (by_diameter[diameter][0], len(by_diameter[diameter]))
        for diameter in sorted(by_diameter, reverse=True)
    ]


def _bar_height(reinforcement: Reinforcement, position: int, rebar: Rebar) -> float:
    """Return the height of a bar's axis from the bottom face (cm)

    Every bar of a layer touches the same edge line, so a bar's axis sits half its diameter from that edge. The edge is the layer's centroid moved back by the area-weighted mean half diameter.

    Args:
        position: Index of the layer in ``reinforcement.chosen_bars``.
    """
    layer = reinforcement.chosen_bars[position]
    mean_half_diameter, _ = reinforcement.get_layer_relative_centroid_with_weight(
        position
    )  # cm
    half_diameter = rebar.diameter_mm / _MM_PER_CM / 2  # cm
    shift = half_diameter - mean_half_diameter  # cm, from the centroid to the axis
    if reinforcement.is_bottom_reinforcement:
        return layer.y_centroid_position + shift
    return layer.y_centroid_position - shift


def _area_ratio(reinforcement: Reinforcement) -> float:
    """Return the required over the provided steel area of a reinforcement

    Raises:
        ValueError: If the required area is not set or no area is provided.
    """
    required_area = reinforcement.required_area  # cm²
    area = reinforcement.area  # cm²
    if required_area is None or area <= 0:
        raise ValueError(
            f"Reinforcement at {reinforcement.center_position:.2f} cm has no required or provided area."
        )
    return required_area / area


def _clamps(reinforcement: Reinforcement) -> list[DetailedClamps]:
    """Build one clamp set per side of a reinforcement that has clamps

    One clamp set serves every layer on a side, so a set shared by several layers is copied once. The U bends at the end of the first layer holding it.
    """
    center = reinforcement.center_position  # cm
    detailed: list[DetailedClamps] = []
    for left in (True, False):
        seen: list[Clamps] = []
        for layer in reinforcement.chosen_bars:
            clamps = layer.get_clamps(left)
            if clamps is None or clamps in seen:
                continue
            seen.append(clamps)
            bar = layer.bars[0]
            position = center - bar.left_length if left else center + bar.right_length
            detailed.append(
                DetailedClamps(
                    diameter_mm=clamps.diameter,
                    steel=reinforcement.steel,
                    quantity=clamps.quantity,
                    width=clamps.width,
                    leg_length=clamps.length,
                    left=left,
                    is_bottom=reinforcement.is_bottom_reinforcement,
                    position=position,
                    source_position=center,
                )
            )
    return detailed


def _stirrups(
    beam: ContinuousBeam,
    structural_beam: RectangularBeam,
    supports: tuple[Support, ...],
) -> list[SpanStirrups]:
    """Copy each span's stirrups and their spacing zones, between the inner faces of its pillars

    The stirrups' outer faces sit on the nominal cover, which sets their outer dimensions and cut length.

    Raises:
        ValueError: If a span's stirrups have no diameter or spacing, or their zones do not cover the stretch between the pillars' faces.
    """
    covers = 2 * RectangularBeam.nominal_covering  # cm
    outer_width = structural_beam.width - covers  # cm
    outer_height = structural_beam.height - covers  # cm
    detailed: list[SpanStirrups] = []
    for index, span in enumerate(beam.spans):
        stirrups = span.stirrups
        span_name = f"{span.start_pillar_id}–{span.end_pillar_id}"
        if stirrups.diameter is None or stirrups.spacing is None:
            raise ValueError(f"Span {span_name} has no stirrup diameter or spacing.")
        start, end = supports[index].right, supports[index + 1].left  # cm
        zones = _clipped_zones(stirrups, start, end)
        if (
            not zones
            or abs(zones[0].start - start) > _ZONE_TOLERANCE
            or abs(zones[-1].end - end) > _ZONE_TOLERANCE
        ):
            raise ValueError(
                f"Span {span_name}: the stirrup zones do not cover the stretch between the pillars' faces ({start:.1f}–{end:.1f} cm)."
            )
        diameter_mm = round(stirrups.diameter * _MM_PER_CM, 2)
        detailed.append(
            SpanStirrups(
                start_pillar_id=span.start_pillar_id,
                end_pillar_id=span.end_pillar_id,
                zones=zones,
                diameter_mm=diameter_mm,
                steel=stirrups.steel,
                outer_width=outer_width,
                outer_height=outer_height,
                cut_length=Stirrups.closed_length_for(
                    outer_width, outer_height, diameter_mm, stirrups.steel
                ),
            )
        )
    return detailed


def _clear_spans(
    beam: ContinuousBeam, height: float, supports: tuple[Support, ...]
) -> list[ClearSpan]:
    """List each span's stretch between the pillars' inner faces

    A side face stays visible below the slab on that side, whatever its level: a lowered slab still covers its thickness.

    Args:
        height: Section height h (cm).
    """
    return [
        ClearSpan(
            start=start.right,
            end=end.left,
            side_heights=(
                _side_height(height, span.supported_slabs[0]),
                _side_height(height, span.supported_slabs[1]),
            ),
        )
        for span, (start, end) in zip(beam.spans, pairwise(supports), strict=True)
    ]


def _skin_bars(
    beam: ContinuousBeam, supports: tuple[Support, ...]
) -> list[DetailedSkinBars]:
    """Lay each span's skin bars between the inner faces of its pillars

    The bars stay in the clear span, without entering the pillars. The rows are evenly spaced in the band between the bottom and top bars: the first one a spacing above the band's start. Spans without skin reinforcement get none.

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.3
    """
    detailed: list[DetailedSkinBars] = []
    for span, (start, end) in zip(beam.spans, pairwise(supports), strict=True):
        skin = span.skin_reinforcement
        if skin is None or skin.layout is None:
            continue
        layout = skin.layout
        detailed.append(
            DetailedSkinBars(
                start_pillar_id=span.start_pillar_id,
                end_pillar_id=span.end_pillar_id,
                diameter_mm=layout.diameter_mm,
                steel=skin.steel,
                heights=tuple(
                    layout.band_start + row * layout.spacing
                    for row in range(1, layout.bars_per_face + 1)
                ),
                start=start.right,
                end=end.left,
            )
        )
    return detailed


def _side_height(height: float, slab: Slab | None) -> float:
    """Return the height of a beam side left visible by the slab on it (cm)"""
    return height if slab is None else height - slab.thickness


def _clipped_zones(
    stirrups: Stirrups, start: float, end: float
) -> tuple[StirrupZone, ...]:
    """Clip a span's stirrup zones to the stretch between its pillars' inner faces

    The design zones run between the theoretical supports, on the pillars' axes, but the stirrups only go between the faces. A zone left without length, lying inside a pillar, is dropped. Stirrups that were not distributed in zones are read as one zone with the chosen spacing.

    Args:
        start: Inner face of the span's start pillar (cm).
        end: Inner face of the span's end pillar (cm).
    """
    zones = stirrups.zones or [StirrupZone(start, end, cast(float, stirrups.spacing))]
    clipped: list[StirrupZone] = []
    for zone in zones:
        zone_start, zone_end = max(zone.start, start), min(zone.end, end)  # cm
        if zone_end - zone_start > _ZONE_TOLERANCE:
            clipped.append(StirrupZone(zone_start, zone_end, zone.spacing))
    return tuple(clipped)
