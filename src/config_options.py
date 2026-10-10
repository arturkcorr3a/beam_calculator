"""Enumerations of the choices accepted by AppConfig.

This module must stay free of project imports so that src.config can import it
without creating circular dependencies.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Aggregate(StrEnum):
    """Coarse aggregate rock type used in the concrete mix.

    References:
        ABNT NBR 6118:2014 — Section 8.2.8
    """

    BASALT = "basalt"
    DIABASE = "diabase"
    GRANITE = "granite"
    GNEISS = "gneiss"
    LIMESTONE = "limestone"
    SANDSTONE = "sandstone"


# REVIEW this names
class ExposureClass(IntEnum):
    """Environmental aggressiveness class (CAA) of the structure.

    References:
        ABNT NBR 6118:2014 — Section 6.4, Table 6.1
    """

    WEAK = 1
    MODERATE = 2
    SEVERE = 3
    VERY_SEVERE = 4


class OccupancyCategory(StrEnum):
    """Building occupancy category used to look up variable usage loads.

    Each value matches a category description in TABLE_10 exactly.

    References:
        ABNT NBR 6120:2019 — Table 10
    """

    RESIDENTIAL = "Residential buildings"
    COMMERCIAL = "Commercial, corporate, and office buildings"
    INDUSTRIAL = "Industrial buildings"
    STAIRS_AND_FOOTBRIDGES = "Stairs and footbridges"
    SCHOOLS = "Schools and educational institutions"
    PASSENGER_STATIONS = "Passenger stations"
    CEILINGS = "Ceilings"
    SPORTS_GYMNASIUMS = "Sports gymnasiums"
    HELIPADS = "Helipads"
    HOSPITALS = "Hospitals"
    HOTELS = "Hotels"
    PENAL_INSTITUTIONS = "Penal institutions (prisons)"
    GARDENS = "Gardens"
    LABORATORIES = "Laboratories"
    NON_RESIDENTIAL_LAUNDRIES = "Non-residential laundries"
    SHOPS = "Shops, commercial centers, and shopping malls"
    MUSEUMS = "Museums and art galleries"
    RESTAURANTS = "Restaurants"
    BALCONIES = "Balconies, verandas, and terraces"
    BANKS = "Banks, bank branches, and financial institutions"
    LIBRARIES = "Libraries"
    CONVENTION_CENTERS = "Convention centers, assembly spaces, theaters, and churches"
    AIRPORTS = "Airports"
    GRANDSTANDS = "Grandstands and bleachers"
    TECHNICAL_AREAS = "Technical areas"
    SUPERMARKETS = "Supermarkets"
    LOBBIES = "Lobbies and entrances"
    CLUBS = "Clubs"
    EXHIBITION_CENTERS = "Exhibition centers"
    CINEMAS = "Cinemas (excluding shopping center cinemas)"
    ROOFS = "Roofs"
    GENERAL_WAREHOUSES = "General use warehouses"
    GOODS_ACCUMULATION = (
        "Locations subject to accumulation of goods, including access zones"
    )
