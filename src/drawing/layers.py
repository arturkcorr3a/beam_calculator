"""Layers and linetypes of the detailing drawings, shared by both renderers"""

from dataclasses import dataclass

CONTINUOUS = "CONTINUOUS"
AXIS_LINETYPE = "EIXO"
DASHED_LINETYPE = "TRACEJADA"

BEAM_OUTLINE = "VIGA-FORMA"
PILLAR = "VIGA-PILAR"
AXIS = "VIGA-EIXO"
MAIN_BAR = "ARM-PRINCIPAL"
CONSTRUCTION_BAR = "ARM-MONTAGEM"
STIRRUP = "ARM-ESTRIBO"
CLAMP = "ARM-GRAMPO"
SECTION_BAR = "ARM-SECAO"
DIMENSION = "COTA"
LAP = "COTA-TRASPASSE"
TEXT = "TEXTO"
CUT = "CORTE"
TABLE = "QUADRO"
SLAB_OUTLINE = "LAJE-CONTORNO"
SLAB_SUPPORT = "LAJE-APOIO"
YIELD_LINE = "LAJE-CHARNEIRA"
SHEET_FRAME = "FOLHA-QUADRO"
SHEET_FRAME_HEAVY = "FOLHA-QUADRO-GROSSO"
BLOCK_HEAVY = "SELO-GROSSO"
BLOCK_LIGHT = "SELO-FINO"
BLOCK_LOGO = "SELO-LOGO"


@dataclass(frozen=True)
class LayerStyle:
    """How one layer is drawn

    Attributes:
        aci: AutoCAD color index used in the DXF.
        linetype: Name of the linetype: CONTINUOUS, EIXO or TRACEJADA.
        lineweight_mm: Plotted line weight (mm).
        screen_color: Color on screen, over a white background.
        description: What the layer holds, as shown in the sheet's legend.
    """

    name: str
    aci: int
    linetype: str
    lineweight_mm: float
    screen_color: str
    description: str


LAYERS: dict[str, LayerStyle] = {
    style.name: style
    for style in (
        LayerStyle(BEAM_OUTLINE, 7, CONTINUOUS, 0.35, "#363636", "Forma da viga"),
        LayerStyle(PILLAR, 8, CONTINUOUS, 0.25, "#6b6b6b", "Pilar"),
        LayerStyle(AXIS, 2, AXIS_LINETYPE, 0.18, "#8a6d00", "Eixo de pilar"),
        LayerStyle(MAIN_BAR, 1, CONTINUOUS, 0.50, "#c62828", "Barra principal"),
        LayerStyle(
            CONSTRUCTION_BAR, 11, CONTINUOUS, 0.30, "#d9686a", "Barra de montagem"
        ),
        LayerStyle(
            STIRRUP, 3, CONTINUOUS, 0.25, "#2e7d32", "Estribo e zona de estribos"
        ),
        LayerStyle(CLAMP, 6, CONTINUOUS, 0.35, "#ad1457", "Grampo"),
        LayerStyle(SECTION_BAR, 1, CONTINUOUS, 0.13, "#c62828", "Barra no corte"),
        LayerStyle(DIMENSION, 5, CONTINUOUS, 0.13, "#1565c0", "Cota"),
        LayerStyle(LAP, 5, DASHED_LINETYPE, 0.13, "#1565c0", "Limite de traspasse"),
        LayerStyle(TEXT, 7, CONTINUOUS, 0.18, "#1a1a1a", "Texto"),
        LayerStyle(CUT, 6, CONTINUOUS, 0.50, "#6a1b9a", "Marca de corte"),
        LayerStyle(TABLE, 7, CONTINUOUS, 0.18, "#1a1a1a", "Quadro"),
        LayerStyle(SLAB_OUTLINE, 7, CONTINUOUS, 0.25, "#363636", "Contorno da laje"),
        LayerStyle(
            SLAB_SUPPORT,
            4,
            CONTINUOUS,
            0.35,
            "#00838f",
            "Apoio da laje",
        ),
        LayerStyle(YIELD_LINE, 30, DASHED_LINETYPE, 0.18, "#e65100", "Charneira"),
        LayerStyle(SHEET_FRAME, 7, CONTINUOUS, 0.70, "#111111", "Quadro da folha"),
        LayerStyle(
            SHEET_FRAME_HEAVY, 7, CONTINUOUS, 1.00, "#111111", "Quadro da folha"
        ),
        LayerStyle(BLOCK_HEAVY, 7, CONTINUOUS, 0.50, "#111111", "Selo, linha grossa"),
        LayerStyle(BLOCK_LIGHT, 7, CONTINUOUS, 0.25, "#111111", "Selo, linha fina"),
        LayerStyle(BLOCK_LOGO, 8, DASHED_LINETYPE, 0.25, "#6b6b6b", "Área do logo"),
    )
}

# Dash pattern of each linetype on paper (mm): dashes positive, gaps negative,
# dots zero, as in a DXF linetype definition
LINETYPE_PATTERNS_MM: dict[str, tuple[float, ...]] = {
    AXIS_LINETYPE: (6.0, -1.0, 0.0, -1.0),
    DASHED_LINETYPE: (1.5, -1.0),
}

LINETYPE_DESCRIPTIONS: dict[str, str] = {
    AXIS_LINETYPE: "Traço-ponto",
    DASHED_LINETYPE: "Tracejada",
}


def layer_style(name: str) -> LayerStyle:
    """Return the style of a layer

    Raises:
        KeyError: If the layer is not in the table.
    """
    try:
        return LAYERS[name]
    except KeyError:
        raise KeyError(f"Unknown drawing layer '{name}'.") from None
