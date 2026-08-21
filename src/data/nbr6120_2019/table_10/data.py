"""ABNT NBR 6120:2019 - Section 5.4 - Table 10: Variable loads data.

Hardcoded values matching the normative table.
"""

from src.data.nbr6120_2019.table_10.model import BuildingCategory, LocationLoad, Table10

# TODO Check this values

_CATEGORIES = (
    BuildingCategory(
        description="Residential buildings",
        locations=(
            LocationLoad(
                description="Bedrooms",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Living rooms, pantries, and kitchens",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Pantry, service area, and laundry",
                distributed_load=2.0,
                notes=(),
            ),
            LocationLoad(
                description="Sports courts",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Party rooms and game rooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Common use areas",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Gym / Fitness center",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Ceilings accessible only for maintenance and without material storage",
                distributed_load=0.1,
                notes=("a", "r"),
            ),
            LocationLoad(
                description="Attics",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors within autonomous units",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Common use corridors",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=3.0,
                notes=(),
            ),
        ),
    ),
    BuildingCategory(
        description="Commercial, corporate, and office buildings",
        locations=(
            LocationLoad(
                description="General use rooms and bathrooms",
                distributed_load=2.5,
                notes=(),
            ),
            LocationLoad(
                description="Sliding archive regions",
                distributed_load=5.0,
                notes=(),
            ),
            LocationLoad(
                description="Call centers",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Corridors within autonomous units",
                distributed_load=2.5,
                notes=(),
            ),
            LocationLoad(
                description="Common use corridors",
                distributed_load=3.0,
                notes=(),
            ),
        ),
    ),
    BuildingCategory(
        description="Industrial buildings",
        locations=(
            LocationLoad(
                description="Cafeterias / Refectories",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Bathrooms and locker rooms",
                distributed_load=2.0,
                notes=(),
            ),
            LocationLoad(
                description="Kitchens",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=(),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=(),
            ),
        ),
    ),
    BuildingCategory(
        description="Stairs and footbridges",
        locations=(
            LocationLoad(
                description="Hospitals",
                distributed_load=3.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Residential, hotels (within autonomous units)",
                distributed_load=2.5,
                notes=("t",),
            ),
            LocationLoad(
                description="Residential, hotels (common use)",
                distributed_load=3.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Commercial buildings, clubs, offices, and libraries",
                distributed_load=3.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Exhibition centers",
                distributed_load=5.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Convention centers, assembly spaces, theaters, and churches",
                distributed_load=5.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Schools",
                distributed_load=3.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Cinemas, commercial centers, and shopping malls",
                distributed_load=4.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Serving grandstands / bleachers",
                distributed_load=5.0,
                notes=("t",),
            ),
            LocationLoad(
                description="With public access",
                distributed_load=3.0,
                notes=("t",),
            ),
            LocationLoad(
                description="Without public access",
                distributed_load=2.5,
                notes=("t",),
            ),
        ),
    ),
    BuildingCategory(
        description="Schools and educational institutions",
        locations=(
            LocationLoad(
                description="Auditoriums with fixed seats",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Auditoriums with movable seats",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Classrooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Dormitories",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Cafes and restaurants",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sports halls and gyms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Dance halls",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms and locker rooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Kitchens",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Laboratories",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sliding archive regions",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sports courts",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Passenger stations",
        locations=(
            LocationLoad(
                description="Accesses, stairs, corridors, and platforms (train, subway, bus, and port stations)",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Ceilings",
        locations=(
            LocationLoad(
                description="Accessible only for maintenance and without material storage",
                distributed_load=0.1,
                notes=("a", "r"),
            ),
        ),
    ),
    BuildingCategory(
        description="Garages and parking lots",
        locations=(
        ),
    ),
    BuildingCategory(
        description="Sports gymnasiums",
        locations=(
            LocationLoad(
                description="Sports practice areas",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Helipads",
        locations=(
        ),
    ),
    BuildingCategory(
        description="Hospitals",
        locations=(
            LocationLoad(
                description="Wards, bedrooms, recovery rooms, and bathrooms",
                distributed_load=2.0,
                notes=(),
            ),
            LocationLoad(
                description="X-ray rooms and operating rooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Laboratories",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Dining rooms, cafes, and restaurants",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=(),
            ),
        ),
    ),
    BuildingCategory(
        description="Hotels",
        locations=(
            LocationLoad(
                description="Bedrooms",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Bathrooms within autonomous units",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Other bathrooms and locker rooms",
                distributed_load=2.0,
                notes=(),
            ),
            LocationLoad(
                description="Sports halls and gyms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Party rooms and game rooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Common use areas",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors within autonomous units",
                distributed_load=1.5,
                notes=(),
            ),
            LocationLoad(
                description="Common use corridors",
                distributed_load=3.0,
                notes=(),
            ),
            LocationLoad(
                description="Restaurants",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Assembly rooms with fixed seats",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Assembly rooms with movable seats",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Kitchens",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=(),
            ),
        ),
    ),
    BuildingCategory(
        description="Penal institutions (prisons)",
        locations=(
            LocationLoad(
                description="Cells",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Gardens",
        locations=(
            LocationLoad(
                description="With possibility of public access",
                distributed_load=3.0,
                notes=("a", "u"),
            ),
            LocationLoad(
                description="Without possibility of public access (maintenance only)",
                distributed_load=1.0,
                notes=("a", "u"),
            ),
        ),
    ),
    BuildingCategory(
        description="Laboratories",
        locations=(
            LocationLoad(
                description="Including equipment (validate case-by-case, respecting the minimum)",
                distributed_load=3.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Non-residential laundries",
        locations=(
            LocationLoad(
                description="Including equipment (validate case-by-case, respecting the minimum)",
                distributed_load=3.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Shops, commercial centers, and shopping malls",
        locations=(
            LocationLoad(
                description="Circulation areas and shops in general",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Shops with metal mezzanine (includes mezzanine self-weight and live load)",
                distributed_load=7.5,
                notes=("a", "v"),
            ),
            LocationLoad(
                description="Metal mezzanine (live load only)",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Food court - public area",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Food court - kitchen and service areas",
                distributed_load=7.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Cinema and theater (live load only, audience with fixed seats)",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Cinema and theater (accesses and corridors)",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Cinema and theater (supporting floor)",
                distributed_load=12.5,
                notes=("a", "w"),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Self-service terminal areas and ATMs",
                distributed_load=12.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Museums and art galleries",
        locations=(
            LocationLoad(
                description="Exhibition areas",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Accesses and corridors",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Restaurants",
        locations=(
            LocationLoad(
                description="Dining hall",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Balconies, sacadas, verandas, and terraces",
        locations=(
            LocationLoad(
                description="Residential",
                distributed_load=2.5,
                notes=("i", "j"),
            ),
            LocationLoad(
                description="Commercial, corporate, and offices",
                distributed_load=3.0,
                notes=("i", "j"),
            ),
            LocationLoad(
                description="With public access (hotels, hospitals, schools, theaters, etc.)",
                distributed_load=4.0,
                notes=("i", "j"),
            ),
        ),
    ),
    BuildingCategory(
        description="Banks, bank branches, and financial institutions",
        locations=(
            LocationLoad(
                description="Offices",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Board and management rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Vaults (validate case-by-case, respecting the minimum)",
                distributed_load=30.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Branch public service areas",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sliding archive regions",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Self-service terminal areas and ATMs",
                distributed_load=12.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Libraries",
        locations=(
            LocationLoad(
                description="Reading rooms (without shelves)",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Reading rooms (with shelves)",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sliding archive regions",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Convention centers, assembly spaces, theaters, and churches",
        locations=(
            LocationLoad(
                description="Auditoriums / Audience areas with fixed seats",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Auditoriums / Audience areas with movable seats",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Accesses and corridors",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Platforms (assembly areas)",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Stage (performance area)",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Airports",
        locations=(
            LocationLoad(
                description="Public access areas, circulations, and bathrooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Shops and duty free areas",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Passport control, security, and X-ray areas",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Baggage reclaim areas (excluding equipment self-weight)",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative areas",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Baggage handling areas (excluding equipment self-weight)",
                distributed_load=10.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Grandstands and bleachers",
        locations=(
            LocationLoad(
                description="With fixed seats",
                distributed_load=4.0,
                notes=("a", "b"),
            ),
            LocationLoad(
                description="With movable seats",
                distributed_load=5.0,
                notes=("a", "b"),
            ),
        ),
    ),
    BuildingCategory(
        description="Technical areas",
        locations=(
            LocationLoad(
                description="Header pipe area (barrilete)",
                distributed_load=1.5,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="General technical areas (outside equipment footprint), except header pipe area",
                distributed_load=3.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Fan room, pressurization, and exhaust rooms",
                distributed_load=3.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Air conditioning rooms (fan coil)",
                distributed_load=4.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Low voltage electrical panel rooms",
                distributed_load=4.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Generator and transformer rooms (with defined layout)",
                distributed_load=3.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Generator and transformer rooms (without defined layout)",
                distributed_load=10.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="UPS rooms (sala de no-breaks)",
                distributed_load=7.5,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Battery rooms",
                distributed_load=10.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="CPD (Data Center / data processing center)",
                distributed_load=5.0,
                notes=("a", "c"),
            ),
            LocationLoad(
                description="Passenger elevator machine room (speed <= 1.0 m/s)",
                distributed_load=30.0,
                notes=("a", "c", "e", "f"),
            ),
            LocationLoad(
                description="Passenger elevator machine room (speed > 1.0 m/s)",
                distributed_load=50.0,
                notes=("a", "c", "e", "f"),
            ),
            LocationLoad(
                description="Passenger elevator pit",
                distributed_load=50.0,
                notes=("f",),
            ),
            LocationLoad(
                description="Pit for motorized lifting platform (reduced mobility)",
                distributed_load=2.5,
                notes=("h",),
            ),
        ),
    ),
    BuildingCategory(
        description="Supermarkets",
        locations=(
            LocationLoad(
                description="Sales floor with shelves and refrigerated/non-refrigerated counters",
                distributed_load=8.0,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Bakery, butcher, fishmonger, cold cuts, and other food handling areas",
                distributed_load=8.0,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Checkout area",
                distributed_load=4.0,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Self-service terminal areas and ATMs",
                distributed_load=12.0,
                notes=("a", "y"),
            ),
            LocationLoad(
                description="Vault rooms and strongrooms",
                distributed_load=10.0,
                notes=("a", "y", "x"),
            ),
        ),
    ),
    BuildingCategory(
        description="Lobbies and entrances (vestíbulos de acesso)",
        locations=(
            LocationLoad(
                description="Residential, hotels, and hospitals (common use)",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Commercial, corporate, and office buildings",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Clubs, schools, and libraries",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Convention centers, assembly spaces, theaters, and churches",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Cinemas, commercial centers, and shopping malls",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Serving grandstands",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Without public access",
                distributed_load=1.5,
                notes=("a",),
            ),
            LocationLoad(
                description="With public access",
                distributed_load=3.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Clubs",
        locations=(
            LocationLoad(
                description="Refectories / Dining rooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Assembly rooms with fixed seats",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Assembly rooms with movable seats",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Gyms / Fitness centers",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sports practice halls",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Dance halls",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Billiard rooms and game rooms",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bowling alleys",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms and locker rooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Kitchens",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Storage rooms",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Administrative rooms",
                distributed_load=2.5,
                notes=("a",),
            ),
            LocationLoad(
                description="Corridors",
                distributed_load=3.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Sports courts",
                distributed_load=5.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Exhibition centers",
        locations=(
            LocationLoad(
                description="Exclusive access for people",
                distributed_load=5.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Exhibition booths area",
                distributed_load=10.0,
                notes=("a", "m"),
            ),
            LocationLoad(
                description="Exhibition area for vehicles and equipment",
                distributed_load=30.0,
                notes=("a", "m"),
            ),
        ),
    ),
    BuildingCategory(
        description="Cinemas (excluding shopping center cinemas)",
        locations=(
            LocationLoad(
                description="Audience areas with fixed seats",
                distributed_load=4.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Bathrooms",
                distributed_load=2.0,
                notes=("a",),
            ),
            LocationLoad(
                description="Accesses and corridors",
                distributed_load=4.0,
                notes=("a",),
            ),
        ),
    ),
    BuildingCategory(
        description="Roofs (coberturas)",
        locations=(
            LocationLoad(
                description="With access only for maintenance or inspection",
                distributed_load=1.0,
                notes=("a", "g", "n", "o"),
            ),
            LocationLoad(
                description="With solar heating or photovoltaic panels",
                distributed_load=1.5,
                notes=("a", "g", "n", "o"),
            ),
        ),
    ),
    BuildingCategory(
        description="General use warehouses",
        locations=(
        ),
    ),
    BuildingCategory(
        description="Locations subject to accumulation of goods, including access zones",
        locations=(
            LocationLoad(
                description="General area",
                distributed_load=7.5,
                notes=("a",),
            ),
        ),
    ),
)

_FOOTNOTES = {
    "a": (
        "Reduction of variable loads is not allowed."
    ),
    "b": (
        "Horizontal forces must be considered in accordance with 6.3. Dynamic effects must be verified."
    ),
    "c": (
        "The path of the equipment to its permanent location must be verified for installation or maintenance. The moving load corresponding to the equipment and transport vehicle may be considered as special, in accordance with ABNT NBR 8681. The possibility of moving the equipment and its components within the technical area must be evaluated. If the layout of the equipment is available, the distributed load indicated may be replaced by the maximum load in operation of the equipment and its bases, together with the uniformly distributed load indicated outside the projection of the equipment. For machine-room-less elevators, the maximum operating weight of the equipment acting on its support points must be considered, in accordance with the elevator design."
    ),
    "d": (
        "Provide for loads due to tanks, reservoirs, pumps, etc. (with their respective bases), distributed over the projection area of these items."
    ),
    "e": (
        "Load on the projection of the elevator shaft."
    ),
    "f": (
        "The forces imposed by the motor, guides, bumpers, pulleys, etc., to be provided by the manufacturer of the passenger elevator, must be calculated in accordance with ABNT NBR NM 207."
    ),
    "g": (
        "For the ceiling of the elevator machine room, check the need to provide concentrated variable loads for the suspension hooks of the equipment (minimum 40 kN per hook)."
    ),
    "h": (
        "Variable load, does not include the self-weight of the lifting platform."
    ),
    "i": (
        "Depending on the case, additional loads must be provided due to future changes, for example: glass enclosure, floor leveling, change of use, etc."
    ),
    "j": (
        "At the edges of balconies, verandas, sacadas, and terraces with guardrails, provide a variable load of 2 kN/m, in addition to the self-weight of the guardrail. Also consider variable horizontal forces in accordance with 6.3."
    ),
    "k": (
        "The action of the equipment as a concentrated load must be verified, represented by a uniformly distributed load of 18.5 kN/m² only on the projection of the equipment (0.9 m x 0.6 m)."
    ),
    "l": (
        "The load applies to double-sided, non-mobile shelving rooms with: a) maximum depth of 30 cm on each face; b) parallel lines of shelving separated by a corridor at least 90 cm wide."
    ),
    "m": (
        "Minimum nominal characteristic load, which must be increased according to the expected weight of the items to be exhibited and any vehicle traffic."
    ),
    "n": (
        "Includes reinforced concrete reservoir covers at the top of buildings."
    ),
    "o": (
        "Verify possibility of water accumulation, in accordance with 5.5."
    ),
    "p": (
        "Storage height corresponds to the maximum available clearance for stacking products. It may be limited by ceilings or other devices that prevent the stacking of products beyond the planned height."
    ),
    "q": (
        "Specific verification may be required for actions of special equipment, as the case may be. If there is a possibility of forklift traffic or similar, the structure must be verified in accordance with 6.6.2."
    ),
    "r": (
        "For inaccessible ceilings and without the possibility of material storage, it is not necessary to consider variable loads due to use."
    ),
    "s": (
        "Due to the high variability of loads in industrial buildings, it is essential to validate the actual loads acting on the structure, according to the uses of the specific areas."
    ),
    "t": (
        "On stairs with cantilevered spans, the effects of alternating loads must be verified. For isolated cantilevered or simply supported steps, calculate the step with a concentrated load of 2.5 kN applied in the most unfavorable position. The verification with concentrated load must be made separately, without simultaneous consideration of the uniformly distributed variable load. Footbridges not inserted in buildings are not part of the scope of this Standard, and ABNT NBR 7188 must be consulted."
    ),
    "u": (
        "For live loads, in addition to permanent loads (waterproofing, soil, and planting). An adequate drainage system must be provided."
    ),
    "v": (
        "The concentrated load can be considered applied over an area of 20 cm x 20 cm (Qk <= 20 kN) or 30 cm x 30 cm (Qk > 20 kN). The value of the concentrated load can be altered depending on the case."
    ),
    "w": (
        "Includes live load, bleacher structure, and other uses under the bleachers. Validate according to the project and expectations of use."
    ),
    "x": (
        "If the strongrooms or vault rooms are detailed in the project (including floor, ceiling, and wall thicknesses), the live load due to use can be adopted as 2.5 kN/m²."
    ),
    "y": (
        "For supermarkets and hypermarkets with sales floors with gondolas and counters with or without refrigeration, the sale of food and other typical products of these locations is assumed. Heavy equipment stores, building materials stores (home centers), etc., must have their design loads defined on a case-by-case basis."
    ),
    "z": (
        "The use of medium pallets (use load of 8 kN to 12 kN, with an average value of 10 kN) and plan dimensions of 1.00 m x 1.20 m is considered, in accordance with ABNT NBR 8334. For structures subject to the use of heavy pallets (use load greater than 12 kN), a specific study must be carried out. The loads of this Standard do not apply to the design of pallet racks and the like, which must be designed in accordance with specific criteria. The effects of the support reactions of the pallet racks (concentrated forces and moments, if any) must be verified."
    ),
}

TABLE_10 = Table10(
    title="Table 10 - Nominal characteristic values of variable loads",
    reference="ABNT NBR 6120:2019",
    description=(
        "Nominal characteristic values for design variable loads (live loads) in buildings according to the type of use and location."
    ),
    units={
        "distributed_load": "kN/m²",
    },
    categories=_CATEGORIES,
    footnotes=_FOOTNOTES,
)
