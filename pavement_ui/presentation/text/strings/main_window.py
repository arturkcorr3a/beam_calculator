"""Texts of the main window: title, menus, actions and status bar (docs/UI_SPEC.md §8)."""

from typing import Final

from pavement_ui.presentation.text.strings.common import APP_NAME, UNTITLED


def window_title(file_name: str | None) -> str:
    """Build the main window title, e.g. "Pavement Designer — exemplo.yaml"

    Args:
        file_name: Name of the open project file, or None when unsaved.
    """
    return f"{APP_NAME} — {file_name or UNTITLED}"


# --- menus --------------------------------------------------------------------
MENU_FILE: Final = "&Arquivo"
MENU_PAVEMENT: Final = "&Pavimento"
MENU_CALCULATION: Final = "&Cálculo"
MENU_TOOLS: Final = "&Ferramentas"
MENU_HELP: Final = "A&juda"
TOOLBAR: Final = "Barra de ferramentas"

# --- actions ------------------------------------------------------------------
NEW: Final = "Novo"
OPEN: Final = "Abrir…"
SAVE: Final = "Salvar"
SAVE_AS: Final = "Salvar como…"
QUIT: Final = "Sair"
FOCUS_PILLARS: Final = "Incluir pilar"
FOCUS_BEAMS: Final = "Incluir viga"
FOCUS_SLABS: Final = "Incluir laje"
CLEAR: Final = "Apagar pavimento…"
VALIDATE: Final = "Validar"
DESIGN: Final = "Dimensionar"
RESULTS: Final = "Resultados…"
CONFIG: Final = "Configurações…"
ISOLATED: Final = "Viga isolada…"
ABOUT: Final = "Sobre"

# --- body ---------------------------------------------------------------------
PLAN_TITLE: Final = "Planta do pavimento"
PLAN_HINT: Final = "coordenadas em metros"
PLAN_ZOOM_IN: Final = "Aproximar"
PLAN_ZOOM_OUT: Final = "Afastar"
PLAN_FIT: Final = "Ajustar à janela"
AXIS_X: Final = "X"
AXIS_Y: Final = "Y"

# --- status bar ---------------------------------------------------------------
STATUS_NOT_VALIDATED: Final = "Estrutura não validada"
STATUS_VALID: Final = "✓ Estrutura válida"
STATUS_INVALID: Final = "✕ {message}"
STATUS_DESIGNING: Final = "Dimensionando…"
STATUS_DESIGN_DONE: Final = "Dimensionamento concluído: {beams} · {slabs}"
STATUS_CURSOR: Final = "X {x} m · Y {y} m"
STATUS_CONFIG: Final = "{concrete} · {steel} · {category} · Pé-direito {height} m"
