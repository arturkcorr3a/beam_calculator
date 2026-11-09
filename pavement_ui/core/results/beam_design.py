"""Read models of a beam's design details shown in its report: loads, stirrups, anchorage."""

from dataclasses import dataclass
from enum import Enum


class LoadSource(Enum):
    """Where a span load comes from"""

    OWN_WEIGHT = "own_weight"
    WALL = "wall"
    SLAB = "slab"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class LoadEntry:
    """One uniform load on a span

    Attributes:
        source: Where the load comes from.
        source_id: Slab reacting on the span (SLAB) or the label of a custom
            load (CUSTOM); None for own weight and wall.
        g_kn_m: Permanent part (kN/m).
        q_kn_m: Variable part (kN/m).
    """

    source: LoadSource
    source_id: str | None
    g_kn_m: float
    q_kn_m: float


@dataclass(frozen=True, slots=True)
class StirrupDesign:
    """Shear design of a span's stirrups

    Attributes:
        d_cm: Effective depth used (cm), the smallest of the span's points.
        vsd_kn: Design shear force V_Sd (kN).
        vrd2_kn: Compressed strut resistance V_Rd2 (kN).
        vc_kn: Concrete contribution V_c (kN).
        vsw_kn: Contribution the stirrups must carry V_sw (kN).
        required_ratio_cm2_cm: Required A_sw/s, at least the minimum (cm²/cm).
        min_ratio_cm2_cm: Minimum A_sw/s (cm²/cm).
        provided_ratio_cm2_cm: A_sw/s of the chosen stirrups at the span ends (cm²/cm).
        max_spacing_cm: Largest spacing allowed for V_Sd (cm).

    References:
        ABNT NBR 6118:2026 — Sections 17.4.1.1.1, 17.4.2.2 and 18.3.3.2
    """

    d_cm: float
    vsd_kn: float
    vrd2_kn: float
    vc_kn: float
    vsw_kn: float
    required_ratio_cm2_cm: float
    min_ratio_cm2_cm: float
    provided_ratio_cm2_cm: float
    max_spacing_cm: float


@dataclass(frozen=True, slots=True)
class AnchorageEntry:
    """Anchorage lengths of one tensioned layer towards one side

    Attributes:
        layer: Layer number; 1 is the closest to the tensioned face.
        left: Whether the bars are anchored towards the left.
        lb_cm: Basic anchorage length l_b (cm).
        lb_nec_cm: Necessary anchorage length l_b,nec (cm).

    References:
        ABNT NBR 6118:2026 — Sections 9.4.2.4 and 9.4.2.5
    """

    layer: int
    left: bool
    lb_cm: float
    lb_nec_cm: float


@dataclass(frozen=True, slots=True)
class BarEntry:
    """One run of identical longitudinal bars of the detailed beam

    Attributes:
        mark: Bar mark (N1, N2, …).
        quantity: Number of bars in the run.
        diameter_mm: Bar diameter (mm).
        bottom: Whether the bars are at the bottom face.
        layer: Layer number; 1 is the closest to the face.
        construction: Whether these are construction bars (no design point).
        center_m: Design point the bars were laid out from, from the beam start (m);
            the first of them after a merge; the run's middle for construction bars.
        start_m: Left end of the straight segment (m).
        end_m: Right end of the straight segment (m).
        left_hook_cm: Extra cut length of the left hook (cm); zero without one.
        right_hook_cm: Extra cut length of the right hook (cm); zero without one.
        total_length_cm: Cut length of one bar, hooks included (cm).
    """

    mark: str
    quantity: int
    diameter_mm: float
    bottom: bool
    layer: int
    construction: bool
    center_m: float
    start_m: float
    end_m: float
    left_hook_cm: float
    right_hook_cm: float
    total_length_cm: float
