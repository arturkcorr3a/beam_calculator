"""pt-BR labels of the NBR 6120 Table 2 (non-bearing) masonry types, by engine description.

Each entry is (full label, short label for tables).
"""

from typing import Final

MASONRY_LABELS: Final[dict[str, tuple[str, str]]] = {
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
}
