"""The V5 reference beam of the drawings, built by hand.

Illustrative data, not produced by the calculation: the hooks' cut lengths follow the
reference drawing's C values, not the bending rules.
"""

from src.detailing.clear_span import ClearSpan
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support

WIDTH = 19.0  # cm
HEIGHT = 50.0  # cm
PILLAR_WIDTH = 19.0  # cm
CENTERS = (0.0, 430.0, 860.0, 1200.0)  # cm
PILLARS = ("P10", "P11", "P12", "P13")
SPACINGS = (17.0, 17.0, 12.0)  # cm


def _bar(
    mark: str,
    *,
    bottom: bool,
    layer: int,
    diameter: float,
    start: float,
    end: float,
    y: float,
    construction: bool = False,
    left_hook: HookGeometry | None = None,
    right_hook: HookGeometry | None = None,
    cut_length: float | None = None,
    quantity: int = 2,
) -> DetailedBar:
    """Build one bar run; the hook cut length makes up the reference drawing's C"""
    straight = end - start
    extra = 0.0 if cut_length is None else cut_length - straight
    hooks = (left_hook is not None) + (right_hook is not None)
    return DetailedBar(
        diameter_mm=diameter,
        steel=Steel.CA50,
        quantity=quantity,
        is_bottom=bottom,
        is_tensioned=not construction,
        layer_index=layer,
        y=y,
        start=start,
        end=end,
        left_hook=left_hook,
        right_hook=right_hook,
        left_hook_length=extra / hooks if left_hook is not None else 0.0,
        right_hook_length=extra / hooks if right_hook is not None else 0.0,
        role=BarRole.CONSTRUCTION if construction else BarRole.MAIN,
        source_positions=() if construction else ((start + end) / 2,),
        mark=mark,
    )


def build_v5() -> DetailingBeam:
    """Return the V5 beam of Appendix A, with marks"""
    supports = tuple(
        Support(center, center - PILLAR_WIDTH / 2, center + PILLAR_WIDTH / 2)
        for center in CENTERS
    )
    stirrups = [
        SpanStirrups(
            start_pillar_id=PILLARS[index],
            end_pillar_id=PILLARS[index + 1],
            zones=(StirrupZone(left.right, right.left, spacing),),
            diameter_mm=5.0,
            steel=Steel.CA50,
            outer_width=14.0,
            outer_height=45.0,
            cut_length=130.0,
            mark="N9",
        )
        for index, (left, right, spacing) in enumerate(
            zip(supports[:-1], supports[1:], SPACINGS, strict=True)
        )
    ]
    clear_spans = [
        ClearSpan(start=left.right, end=right.left, side_heights=(HEIGHT, HEIGHT))
        for left, right in zip(supports[:-1], supports[1:], strict=True)
    ]
    frame = HookGeometry(pin_diameter=15.0, tip_length=30.0)
    standard = HookGeometry(pin_diameter=5.0, tip_length=8.0)
    bars = [
        _bar(
            "N1",
            bottom=False,
            layer=0,
            diameter=10,
            start=-7,
            end=95,
            y=46.5,
            left_hook=frame,
            cut_length=136,
        ),
        _bar(
            "N2",
            bottom=False,
            layer=0,
            diameter=5,
            start=75,
            end=370,
            y=46.75,
            construction=True,
        ),
        _bar("N3", bottom=False, layer=0, diameter=12.5, start=350, end=520, y=46.375),
        _bar("N4", bottom=False, layer=1, diameter=10, start=380, end=480, y=43.25),
        _bar(
            "N5",
            bottom=False,
            layer=0,
            diameter=5,
            start=500,
            end=790,
            y=46.75,
            construction=True,
        ),
        _bar("N6", bottom=False, layer=0, diameter=12.5, start=770, end=960, y=46.375),
        _bar(
            "N7",
            bottom=False,
            layer=0,
            diameter=5,
            start=940,
            end=1090,
            y=46.75,
            construction=True,
        ),
        _bar(
            "N8",
            bottom=False,
            layer=0,
            diameter=10,
            start=1070,
            end=1207,
            y=46.5,
            right_hook=HookGeometry(pin_diameter=15.0, tip_length=58.0),
            cut_length=199,
        ),
        _bar(
            "N10",
            bottom=True,
            layer=0,
            diameter=10,
            start=-7,
            end=445,
            y=3.5,
            left_hook=standard,
            cut_length=464,
        ),
        _bar("N11", bottom=True, layer=1, diameter=8, start=80, end=340, y=6.4),
        _bar("N12", bottom=True, layer=0, diameter=10, start=415, end=875, y=3.5),
        _bar(
            "N13",
            bottom=True,
            layer=0,
            diameter=10,
            start=845,
            end=1207,
            y=3.5,
            right_hook=standard,
            cut_length=374,
        ),
    ]
    clamps = [
        DetailedClamps(
            diameter_mm=6.3,
            steel=Steel.CA50,
            quantity=2,
            width=13.0,
            leg_length=40.0,
            left=False,
            is_bottom=True,
            position=1207.0,
            source_position=bars[-1].source_positions[0],
            mark="N14",
        )
    ]
    return DetailingBeam(
        beam_id="V5",
        width=WIDTH,
        height=HEIGHT,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=supports,
        bars=bars,
        clamps=clamps,
        stirrups=stirrups,
        clear_spans=clear_spans,
    )


def bar(beam: DetailingBeam, mark: str) -> DetailedBar:
    """Return the bar run of a beam with a mark"""
    return next(item for item in beam.bars if item.mark == mark)
