from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeformationCheckResult:
    """Snapshot of an excessive-deformation (ELS-DEF) verification at one height

    Loads and moments keep the checker's units: per unit length for beams (kN/m,
    kN/cm) and per unit area for slabs (kN/m², kN/cm²), whose section is a strip
    of ``width`` (cm).

    Attributes:
        height: Cross-section height verified (cm).
        effective_depth: Effective depth d (cm).
        span: Span used for the deflection and its limit (cm).
        width: Section width; 100 cm for slabs (cm).
        permanent_load: Permanent load g, including own weight for slabs (kN/m or kN/m²).
        variable_load: Variable load q (kN/m or kN/m²).
        design_load: Quasi-permanent combination load (kN/cm or kN/cm²).
        service_moment: Service moment Ms (kN.cm).
        cracking_moment: Cracking moment Mr (kN.cm).
        is_cracked: Whether Ms exceeds Mr (stage II).
        equivalent_moment_of_inertia: Branson's equivalent inertia, capped at the gross one (cm⁴).
        immediate_deflection: Immediate deflection (cm).
        long_term_deflection: Total deflection at t = ∞, including creep (cm).
        acceptable_deflection: Visual sensory limit l/250 (cm).
        passes: Whether the long-term deflection is within the limit.

    References:
        ABNT NBR 6118:2014 — Section 17.3.2
    """

    height: float
    effective_depth: float
    span: float
    width: float
    permanent_load: float
    variable_load: float
    design_load: float
    service_moment: float
    cracking_moment: float
    is_cracked: bool
    equivalent_moment_of_inertia: float
    immediate_deflection: float
    long_term_deflection: float
    acceptable_deflection: float
    passes: bool
