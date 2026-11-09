"""Beam drawings without reinforcement, for the design report: elevation and cross section

They reuse the detailing sheet's pieces (pillars, faces, span and axis dimensions, title),
so the report shows the same geometry as the sheet.
"""

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.layout import (
    AXIS_OVERRUN_MM,
    PILLAR_NAME_DROP_MM,
    beam_faces,
    geometry_dimension_rows,
    pillars,
    title,
)
from src.drawing.primitives import Drawing
from src.drawing.sections import draw_plain_section


def build_beam_outline(
    detailing: DetailingBeam, config: DrawingConfig = DEFAULT_CONFIG
) -> Drawing:
    """Return the beam's elevation without reinforcement

    Pillars with their axes and names, the beam faces, the clear-span and axis
    dimension rows and the title. The pillars go down the shortest stretch, since
    there are no hooks to show.
    """
    y_bot = -config.pillar_below_min
    axis_bottom = y_bot - config.paper(PILLAR_NAME_DROP_MM + AXIS_OVERRUN_MM)
    drawing = pillars(detailing, config, y_bot, axis_bottom)
    drawing.extend(beam_faces(detailing))
    drawing.extend(geometry_dimension_rows(detailing, config))
    drawing.extend(title(detailing, config))
    return drawing


def build_beam_section(
    detailing: DetailingBeam, config: DrawingConfig = DEFAULT_CONFIG
) -> Drawing:
    """Return the beam's cross section without reinforcement and title, its corner at the origin"""
    return draw_plain_section(detailing.width, detailing.height, (0.0, 0.0), config)
