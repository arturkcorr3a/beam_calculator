"""Texts of the isolated beam calculator."""

from typing import Final

TITLE: Final = "Calculadora de viga isolada"
SECTION: Final = "Seção"
WIDTH: Final = "Largura b (≥ 12)"
HEIGHT: Final = "Altura h"
CONCRETE: Final = "Concreto"
FROM_CONFIG: Final = "Das configurações gerais"
STEEL: Final = "Aço"
AGG_SIZE: Final = "Dim. máx. agregado"
MAX_BAR_TYPES: Final = "Máx. diâmetros"
MAX_LAYERS: Final = "Máx. camadas"
CEILING_HEIGHT: Final = "Pé-direito"
CM_VALUE: Final = "{value} cm"
M_VALUE: Final = "{value} m"
DESIGN: Final = "Dimensionar"
DESIGNING: Final = "Dimensionando…"
SCHEME: Final = "Esquema da viga"
EMPTY: Final = "Informe os dados e clique em Dimensionar."

# --- spans and pillars ----------------------------------------------------------
SPANS_PILLARS: Final = "Vãos e pilares"
COL_SPAN: Final = "Vão"
COL_LENGTH: Final = "Comprimento"
COL_PILLAR: Final = "Pilar"
COL_PILLAR_WIDTH: Final = "Largura (ao longo)"
COL_PILLAR_DEPTH: Final = "Profundidade"
SPAN_NAME: Final = "V{n}"
PILLAR_NAME: Final = "P{n}"
ADD_SPAN: Final = "+ Vão"
REMOVE_SPAN: Final = "− Vão"
SPANS_HINT: Final = (
    "Comprimento entre os eixos dos pilares. A profundidade do pilar deve cobrir b."
)

# --- loads ----------------------------------------------------------------------
LOADS: Final = "Cargas"
COL_LOAD: Final = "Carga"
COL_LOAD_SPAN: Final = "Vão"
COL_G: Final = "g (kN/m)"
COL_Q: Final = "q (kN/m)"
ALL_SPANS: Final = "Todos"
ADD_OWN_WEIGHT: Final = "+ Peso próprio"
ADD_WALL: Final = "+ Parede"
ADD_CUSTOM: Final = "+ Carga"
EDIT_LOAD: Final = "Editar"
REMOVE_LOAD: Final = "Remover"
LOAD_OWN_WEIGHT: Final = "Peso próprio (25 kN/m³ × b × h)"
LOAD_WALL: Final = "Parede {masonry} {thickness} cm, h = {height} m"
LOADS_HINT: Final = "Remover um vão remove as cargas aplicadas só nele."

# --- load dialogs ---------------------------------------------------------------
WALL_DIALOG: Final = "Carga de parede"
WALL_HEIGHT: Final = "Altura da parede"
CUSTOM_DIALOG: Final = "Carga adicional"
LOAD_SCOPE: Final = "Aplicar no vão"
LOAD_LABEL: Final = "Descrição"
LOAD_LABEL_DEFAULT: Final = "Carga adicional"
LOAD_VALUE: Final = "Valor"
LOAD_KIND: Final = "Tipo"
LOAD_PERMANENT: Final = "Permanente (g)"
LOAD_VARIABLE: Final = "Variável (q)"
LOAD_PSI_2: Final = "ψ2"
LOAD_PSI_2_HINT: Final = "Fator de redução quase permanente, usado na flecha (ELS)."
UNIT_KN_M: Final = "kN/m"

# --- scheme ---------------------------------------------------------------------
SCHEME_LOAD: Final = "g = {g} · q = {q} kN/m"
SCHEME_LENGTH: Final = "{value} m"

# --- results --------------------------------------------------------------------
TAB_REPORT: Final = "Relatório"
TAB_DRAWING: Final = "Desenho"
