from math import isclose, pi, tan


def cotan(alpha: float) -> float:
    """
    Returns the cotangent of an angle in radians.
    Raises ValueError if the angle is 0 or pi, where cotangent is undefined.
    """
    if isclose(alpha % pi, 0, abs_tol=1e-5):
        raise ValueError("Cotangent is undefined for angles 0 and pi radians.")

    if isclose(alpha % pi, pi / 2, abs_tol=1e-5):
        return 0.0

    return 1 / tan(alpha)
