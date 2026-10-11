"""pt-BR labels of NBR 6120 Table 10 slab usages, by engine description.

Residential usages are complete; usages of other categories fall back to the
engine's text until translated [Decisão, docs/UI_SPEC.md §7.3].
"""

from typing import Final

USAGE_LABELS: Final[dict[str, str]] = {
    "Bedrooms": "Dormitórios",
    "Living rooms, pantries, and kitchens": "Salas, copas e cozinhas",
    "Bathrooms": "Banheiros",
    "Pantry, service area, and laundry": "Despensa, área de serviço e lavanderia",
    "Sports courts": "Quadras esportivas",
    "Party rooms and game rooms": "Salão de festas e salão de jogos",
    "Common use areas": "Áreas de uso comum",
    "Gym / Fitness center": "Academia",
    "Ceilings accessible only for maintenance and without material storage": (
        "Forros acessíveis só para manutenção"
    ),
    "Attics": "Sótãos",
    "Corridors within autonomous units": "Corredores dentro de unidades autônomas",
    "Common use corridors": "Corredores de uso comum",
    "Storage rooms": "Depósitos",
}
