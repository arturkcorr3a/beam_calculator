"""SINAPI rebar prices (insumos), reference October 2026.

National average (média Brasil) material prices, so no state and no
desoneração regime apply. The CA-25 dowel bars (barra de transferência,
codes 42402 to 42405) are left out: they serve pavements, not rebar.

References:
    SINAPI — Insumos, família 43055, referência 10/2026, média Brasil.
    Available at: https://orcamentador.com.br/insumos/?familia=43055.
"""

from src.data.sinapi_2026_10.steel_prices.model import SteelPrice, SteelPriceTable
from src.properties.steel import Steel

_ITEMS = (
    SteelPrice(
        code=32,
        description="ACO CA-50, 6,3 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(6.3,),
        cut_and_bent=False,
        price_per_kg=8.37,
    ),
    SteelPrice(
        code=33,
        description="ACO CA-50, 8,0 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(8.0,),
        cut_and_bent=False,
        price_per_kg=8.42,
    ),
    SteelPrice(
        code=34,
        description="ACO CA-50, 10,0 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(10.0,),
        cut_and_bent=False,
        price_per_kg=7.94,
    ),
    SteelPrice(
        code=34341,
        description="ACO CA-25, 32,0 MM, VERGALHAO",
        steel=Steel.CA25,
        diameters_mm=(32.0,),
        cut_and_bent=False,
        price_per_kg=9.61,
    ),
    SteelPrice(
        code=34449,
        description="ACO CA-50, 6,3 MM, DOBRADO E CORTADO",
        steel=Steel.CA50,
        diameters_mm=(6.3,),
        cut_and_bent=True,
        price_per_kg=9.31,
    ),
    SteelPrice(
        code=43053,
        description="ACO CA-25, 6,3 MM OU 8,0 MM, VERGALHAO",
        steel=Steel.CA25,
        diameters_mm=(6.3, 8.0),
        cut_and_bent=False,
        price_per_kg=7.62,
    ),
    SteelPrice(
        code=43054,
        description="ACO CA-25, 10,0 MM, OU 12,5 MM, OU 16,0 MM, OU 20,0 MM, OU 25,0 MM, VERGALHAO",
        steel=Steel.CA25,
        diameters_mm=(10.0, 12.5, 16.0, 20.0, 25.0),
        cut_and_bent=False,
        price_per_kg=8.53,
    ),
    SteelPrice(
        code=43055,
        description="ACO CA-50, 12,5 MM OU 16,0 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(12.5, 16.0),
        cut_and_bent=False,
        price_per_kg=6.88,
    ),
    SteelPrice(
        code=43056,
        description="ACO CA-50, 20,0 MM OU 25,0 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(20.0, 25.0),
        cut_and_bent=False,
        price_per_kg=7.93,
    ),
    SteelPrice(
        code=43057,
        description="ACO CA-50, 32,0 MM, VERGALHAO",
        steel=Steel.CA50,
        diameters_mm=(32.0,),
        cut_and_bent=False,
        price_per_kg=8.71,
    ),
    SteelPrice(
        code=43058,
        description="ACO CA-50, 10,0 MM, OU 12,5 MM, OU 16,0 MM, OU 20,0 MM, DOBRADO E CORTADO",
        steel=Steel.CA50,
        diameters_mm=(10.0, 12.5, 16.0, 20.0),
        cut_and_bent=True,
        price_per_kg=7.90,
    ),
    SteelPrice(
        code=43059,
        description="ACO CA-60, 4,2 MM, OU 5,0 MM, OU 6,0 MM, OU 7,0 MM, VERGALHAO",
        steel=Steel.CA60,
        diameters_mm=(4.2, 5.0, 6.0, 7.0),
        cut_and_bent=False,
        price_per_kg=7.51,
    ),
    SteelPrice(
        code=43060,
        description="ACO CA-60, 8,0 MM OU 9,5 MM, VERGALHAO",
        steel=Steel.CA60,
        diameters_mm=(8.0, 9.5),
        cut_and_bent=False,
        price_per_kg=6.54,
    ),
    SteelPrice(
        code=43061,
        description="ACO CA-60, 4,2 MM OU 5,0 MM, DOBRADO E CORTADO",
        steel=Steel.CA60,
        diameters_mm=(4.2, 5.0),
        cut_and_bent=True,
        price_per_kg=7.87,
    ),
    SteelPrice(
        code=43062,
        description="ACO CA-60, 6,0 MM OU 7,0 MM, DOBRADO E CORTADO",
        steel=Steel.CA60,
        diameters_mm=(6.0, 7.0),
        cut_and_bent=True,
        price_per_kg=8.33,
    ),
)


STEEL_PRICES = SteelPriceTable(
    title="SINAPI - Steel prices",
    reference="SINAPI — Insumos, família 43055, 10/2026, média Brasil",
    description=(
        "Unit prices of rebar by grade and diameter, straight (vergalhão) "
        "or cut and bent (dobrado e cortado)."
    ),
    units={"price": "R$/kg"},
    items=_ITEMS,
)
