"""pt-BR labels of the NBR 6120 Table 2 masonry types, by engine description.

Each entry is (full label, short label for tables).
"""

from typing import Final

MASONRY_LABELS: Final[dict[str, tuple[str, str]]] = {
    # non-bearing
    "Hollow concrete block (Class C - ABNT NBR 6136)": (
        "Bloco vazado de concreto (Classe C – NBR 6136)",
        "Concreto vazado",
    ),
    "Hollow ceramic block (Horizontal holes - ABNT NBR 15270-1)": (
        "Bloco cerâmico vazado (furos horizontais – NBR 15270-1)",
        "Cerâm. vazado",
    ),
    "Autoclaved aerated concrete block (Class C25 - ABNT NBR 13438)": (
        "Bloco de concreto celular autoclavado (C25 – NBR 13438)",
        "Concreto celular",
    ),
    "Glass block (decorative, non-fire-rated)": (
        "Bloco de vidro (decorativo, sem resistência ao fogo)",
        "Vidro",
    ),
    # structural
    "Hollow concrete block (Classes A and B - ABNT NBR 6136)": (
        "Bloco vazado de concreto (Classes A e B – NBR 6136)",
        "Concreto vazado estr.",
    ),
    "Hollow ceramic block with solid walls (Vertical holes - ABNT NBR 15270-1)": (
        "Bloco cerâmico de paredes maciças (furos verticais – NBR 15270-1)",
        "Cerâm. paredes maciças",
    ),
    "Hollow ceramic block with hollow walls (Vertical holes - ABNT NBR 15270-1)": (
        "Bloco cerâmico de paredes vazadas (furos verticais – NBR 15270-1)",
        "Cerâm. paredes vazadas",
    ),
    "Solid ceramic brick (ABNT NBR 15270-1)": (
        "Tijolo cerâmico maciço (NBR 15270-1)",
        "Tijolo maciço",
    ),
    "Hollow calcium silicate block (Class E - ABNT NBR 14974-1)": (
        "Bloco sílico-calcário vazado (Classe E – NBR 14974-1)",
        "Sílico-calc. vazado",
    ),
    "Perforated calcium silicate block (Classes E, F and G - ABNT NBR 14974-1)": (
        "Bloco sílico-calcário perfurado (Classes E, F e G – NBR 14974-1)",
        "Sílico-calc. perfurado",
    ),
}
