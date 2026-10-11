"""Texts of message boxes and file errors (docs/UI_SPEC.md §9.2, §9.3)."""

from typing import Final

# --- buttons ------------------------------------------------------------------
CANCEL: Final = "Cancelar"
CLEAR: Final = "Apagar"
NEW: Final = "Novo"
SAVE: Final = "Salvar"

# --- inclusion ----------------------------------------------------------------
INCLUDE_PILLAR_TITLE: Final = "Incluir pilar"
INCLUDE_BEAM_TITLE: Final = "Incluir viga"
INCLUDE_SLAB_TITLE: Final = "Incluir laje"
PILLAR_NOT_CREATED: Final = "O pilar não foi criado."
BEAM_NOT_CREATED: Final = "A viga não foi criada."
SLAB_NOT_CREATED: Final = "A laje não foi criada."

# --- validation and design ----------------------------------------------------
VALIDATE_TITLE: Final = "Validar estrutura"
STRUCTURE_INVALID: Final = "A estrutura não é válida."
STRUCTURE_VALID: Final = "Estrutura válida."
STRUCTURE_VALID_DETAIL: Final = (
    "Nenhum erro encontrado em vigas e lajes. O pavimento pode ser dimensionado."
)
DESIGN_TITLE: Final = "Dimensionar"
DESIGN_INTERRUPTED: Final = "O dimensionamento foi interrompido."
DESIGN_UNEXPECTED: Final = "Ocorreu um erro inesperado no cálculo."

# --- confirmations ------------------------------------------------------------
CLEAR_TITLE: Final = "Apagar pavimento"
CLEAR_QUESTION: Final = "Apagar todos os pilares, vigas e lajes?"
CLEAR_DETAIL: Final = (
    "Esta ação não pode ser desfeita. "
    "A numeração dos novos elementos continua de onde parou."
)
NEW_TITLE: Final = "Novo projeto"
NEW_QUESTION: Final = "Começar um novo projeto?"
NEW_DETAIL: Final = "O pavimento atual e as configurações serão descartados."
SAVE_INVALID_QUESTION: Final = "A estrutura não é válida. Salvar assim mesmo?"
SAVE_INVALID_DETAIL: Final = (
    "{error}\n\nSe houver referências a elementos excluídos, "
    "o arquivo poderá não abrir."
)

# --- files --------------------------------------------------------------------
OPEN_FILE_TITLE: Final = "Abrir arquivo"
SAVE_FILE_TITLE: Final = "Salvar arquivo"
OPEN_FAILED: Final = "Não foi possível abrir o arquivo."
SAVE_FAILED: Final = "Não foi possível salvar o arquivo."
FILE_NOT_FOUND: Final = "Arquivo não encontrado: {path}."
FILE_INVALID_YAML: Final = "O arquivo não é um YAML válido (linha {line})."
FILE_INVALID_CONTENT: Final = "Conteúdo inválido: {detail}"
FILE_WRITE_FAILED: Final = "Não foi possível gravar o arquivo: {detail}."

# --- isolated beam ------------------------------------------------------------
ISOLATED_TITLE: Final = "Viga isolada"
ISOLATED_NOT_VERIFIED: Final = "Dimensionamento não verificado."
ISOLATED_NOT_VERIFIED_DETAIL: Final = (
    "A seção {width} × {height} cm não pôde ser dimensionada. "
    "Aumente a seção ou a classe do concreto.\n\n{reason}"
)
ISOLATED_INVALID_INPUT: Final = "Dados inválidos."

# --- about --------------------------------------------------------------------
ABOUT_TITLE: Final = "Sobre"
ABOUT_TEXT: Final = (
    "<b>Pavement Designer</b><br>"
    "Pré-dimensionamento e dimensionamento de pavimentos de concreto armado "
    "(NBR 6118, NBR 6120)."
)
