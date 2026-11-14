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

# --- file dialogs -------------------------------------------------------------
FILE_FILTER: Final = "Pavimento (*.yaml *.yml)"
FILE_EXTENSION: Final = ".yaml"

# --- report export ------------------------------------------------------------
EXPORT_PDF_TITLE: Final = "Exportar relatório em PDF"
PDF_FILTER: Final = "PDF (*.pdf)"
PDF_EXTENSION: Final = ".pdf"
EXPORT_FAILED: Final = "Não foi possível exportar o relatório."
EXPORT_DXF_TITLE: Final = "Baixar desenho em DXF"
EXPORT_DRAWING_PDF_TITLE: Final = "Baixar desenho em PDF"
DXF_FILTER: Final = "DXF (*.dxf)"
DXF_EXTENSION: Final = ".dxf"
EXPORT_DRAWING_FAILED: Final = "Não foi possível gravar o desenho."
BUNDLE_TITLE: Final = "Baixar tudo"
BUNDLE_FOLDER_TITLE: Final = "Escolher a pasta do arquivo ZIP"
BUNDLE_FILE_NAME: Final = "{name}_resultados.zip"
BUNDLE_FAILED: Final = "Não foi possível gravar o arquivo ZIP."
BUNDLE_OVERWRITE_QUESTION: Final = "Substituir o arquivo existente?"
BUNDLE_OVERWRITE_DETAIL: Final = "{path} já existe e será substituído."
BUNDLE_REPLACE: Final = "Substituir"
BUNDLE_DONE: Final = "Arquivo ZIP gravado."
BUNDLE_DONE_DETAIL: Final = (
    "{path}\n\n{reports} relatórios e {sheets} folhas de detalhamento (PDF e DXF)."
)

# --- configuration dialog (docs/UI_SPEC.md §9.1) ------------------------------
CONFIG_TITLE: Final = "Configurações gerais do projeto"
CONFIG_RESTORE: Final = "Restaurar padrões"
CONFIG_OK: Final = "OK"
CONFIG_MATERIALS: Final = "Materiais"
CONFIG_CONCRETE: Final = "Classe do concreto"
CONFIG_STEEL: Final = "Aço"
CONFIG_AGGREGATE: Final = "Tipo de agregado"
CONFIG_AGG_SIZE: Final = "Dimensão máx. do agregado"
CONFIG_DETAILING: Final = "Detalhamento das armaduras"
CONFIG_MAX_BAR_TYPES: Final = "Máx. de diâmetros diferentes"
CONFIG_PER_REINFORCEMENT: Final = "por armadura"
CONFIG_MAX_LAYERS: Final = "Máx. de camadas"
CONFIG_LAYERS: Final = "camadas"
CONFIG_BUILDING: Final = "Edificação"
CONFIG_EXPOSURE: Final = "Classe de agressividade"
CONFIG_CATEGORY: Final = "Categoria da edificação"
CONFIG_CATEGORY_HINT: Final = (
    "Define os usos disponíveis para as lajes (NBR 6120, Tabela 10)."
)
CONFIG_CEILING: Final = "Pé-direito"
CONFIG_LOG: Final = "Memorial de cálculo (não é salvo no arquivo)"
CONFIG_LOG_LEVEL: Final = "Nível de detalhe"
CONFIG_LOG_OUTPUT: Final = "Saída"
CONFIG_LOG_HINT: Final = "Pasta: {folder}\nArquivo: beam_calculator_<data-hora>.log"
