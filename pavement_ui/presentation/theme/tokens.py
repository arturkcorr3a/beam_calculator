"""Design tokens taken from the mockups — the single source of colors and metrics.

Every color used by the stylesheet or by custom painting comes from here
(docs/UI_SPEC.md §7.1).
"""

from typing import Final

# --- Surfaces -----------------------------------------------------------------
WINDOW_BG: Final = "#EEF0F2"
CHROME_BG: Final = "#F7F8F9"
STATUS_BG: Final = "#DDE1E5"
SURFACE: Final = "#FFFFFF"
BORDER: Final = "#C8CDD2"
BORDER_INPUT: Final = "#A9B1B9"

# --- Text ---------------------------------------------------------------------
TEXT: Final = "#1C2126"
TEXT_MUTED: Final = "#545D66"

# --- Accent and states --------------------------------------------------------
ACCENT: Final = "#1D5AA6"
ACCENT_HOVER: Final = "#174C8D"
SELECTION_ROW: Final = "#D6E4F5"
OK: Final = "#0E6B38"
OK_BG: Final = "#E5F4EA"
ERROR: Final = "#A3261A"
ERROR_BG: Final = "#FCEBE9"
WARNING: Final = "#8A4B00"
WARNING_BG: Final = "#FFF3DF"

# --- Plan ---------------------------------------------------------------------
PLAN_SLAB: Final = "#E4EEFA"
PLAN_SLAB_SELECTED: Final = "#BCD3F0"
PLAN_SLAB_LOWERED: Final = "#F6EAD7"
PLAN_SLAB_LOWERED_SELECTED: Final = "#EBCFA5"
PLAN_BEAM_FILL: Final = "#AAB4BE"
PLAN_BEAM_OUTLINE: Final = "#5F6A75"
PLAN_PILLAR: Final = "#2A3138"
PLAN_GRID: Final = "#E2E6EA"

# --- Diagrams and section drawing ---------------------------------------------
DIAGRAM_MOMENT_LINE: Final = "#1D5AA6"
DIAGRAM_MOMENT_FILL: Final = "#DBE6F4"
DIAGRAM_SHEAR_LINE: Final = "#B5521B"
DIAGRAM_SHEAR_FILL: Final = "#FDE7D9"
BAR: Final = "#A3261A"
STIRRUP: Final = "#1D5AA6"
CONCRETE: Final = "#E9ECEF"

# --- Typography and metrics ---------------------------------------------------
UI_FONT_FAMILY: Final = "IBM Plex Sans"
MONO_FONT_FAMILY: Final = "IBM Plex Mono"
UI_FONT_POINT_SIZE: Final = 10
RADIUS_PX: Final = 4
SPACING_PX: Final = 6
MARGIN_PX: Final = 8
