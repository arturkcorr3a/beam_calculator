"""Texts of the Pilares / Vigas / Lajes side panels."""

from typing import Final

# --- units --------------------------------------------------------------------
UNIT_M: Final = "m"
UNIT_CM: Final = "cm"

# --- tabs ---------------------------------------------------------------------
TAB_PILLARS: Final = "Pilares ({n})"
TAB_BEAMS: Final = "Vigas ({n})"
TAB_SLABS: Final = "Lajes ({n})"

# --- pillars ------------------------------------------------------------------
PILLAR_FORM: Final = "Novo pilar"
PILLAR_X: Final = "X do centro"
PILLAR_Y: Final = "Y do centro"
PILLAR_WIDTH: Final = "Largura (em X)"
PILLAR_DEPTH: Final = "Profundidade (em Y)"
PILLAR_HINT: Final = (
    "Cada dimensão ≥ 14 cm e área ≥ 360 cm² (NBR 6118 §13.2.3). "
    "O ID é gerado automaticamente."
)
PILLAR_ADD: Final = "Incluir pilar"
PILLAR_LIST: Final = "Pilares cadastrados"
PILLAR_REMOVE: Final = "Excluir pilar selecionado"
COL_ID: Final = "ID"
COL_X: Final = "X (m)"
COL_Y: Final = "Y (m)"
COL_WIDTH: Final = "Largura (cm)"
COL_DEPTH: Final = "Profund. (cm)"

# --- pillar choice ------------------------------------------------------------
PILLAR_CHOICE: Final = "{id}  ({x}; {y}) m"
NO_PILLARS_HINT: Final = "Nenhum pilar cadastrado: inclua pilares na aba Pilares."

# --- beams --------------------------------------------------------------------
BEAM_FORM: Final = "Nova viga contínua"
BEAM_PILLARS: Final = "Pilares de apoio"
BEAM_PILLARS_HINT: Final = "Marque os pilares da viga: mínimo 2, em qualquer ordem."
BEAM_REFERENCE: Final = "Pilar de referência"
BEAM_WIDTH: Final = "Largura bw (≥ 12)"
BEAM_ALIGNMENT: Final = "Alinhamento"
BEAM_ADD: Final = "Incluir viga"
BEAM_HINT: Final = "A altura h é pré-dimensionada no cálculo."
BEAM_LIST: Final = "Vigas cadastradas"
BEAM_REMOVE: Final = "Excluir viga selecionada"
COL_PILLARS: Final = "Pilares"
COL_REFERENCE: Final = "Ref."
COL_BW: Final = "bw"
COL_ALIGNMENT: Final = "Alinh."
COL_WALL: Final = "Parede"
PILLAR_LIST_JOIN: Final = ", "
WALL_CELL: Final = "{masonry} {thickness} cm"
WALL_NONE_CELL: Final = "Sem parede"
WALL_TOOLTIP: Final = "{masonry}, {thickness} cm, revestimento {coating} cm por face"

# --- wall ---------------------------------------------------------------------
WALL_FORM: Final = "Parede sobre a viga"
WALL_PRESENT: Final = "Com parede sobre a viga"
WALL_MASONRY: Final = "Alvenaria"
WALL_THICKNESS: Final = "Espessura nominal"
WALL_COATING: Final = "Revestimento"
WALL_HEIGHT_HINT: Final = "Altura da parede = pé-direito do projeto ({height} m)."
CM_ITEM: Final = "{value} cm"
COATING_ITEM: Final = "{value} cm por face"

# --- slabs --------------------------------------------------------------------
SLAB_FORM: Final = "Nova laje"
SLAB_CORNERS: Final = "Pilares de canto"
SLAB_CORNERS_HINT: Final = "Marque exatamente 4 pilares, em qualquer ordem."
SLAB_USAGE: Final = "Uso"
SLAB_USAGE_HINT: Final = "Opções da categoria “{category}” (NBR 6120, Tabela 10)."
SLAB_NO_USAGES_HINT: Final = (
    "A categoria “{category}” não tem usos de laje na NBR 6120, Tabela 10."
)
SLAB_LOWERED: Final = "Rebaixo (≥ 0)"
SLAB_HINT: Final = "A espessura é pré-dimensionada no cálculo."
SLAB_ADD: Final = "Incluir laje"
SLAB_LIST: Final = "Lajes cadastradas"
SLAB_REMOVE: Final = "Excluir laje selecionada"
COL_CORNERS: Final = "Pilares de canto"
COL_USAGE: Final = "Uso"
COL_LOWERED: Final = "Rebaixo (cm)"
