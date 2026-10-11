"""Conversions between engine values and the core's stable keys and units."""

from enum import Enum

_CM_PER_M = 100.0


def to_key(member: Enum) -> str:
    """Return the stable key of an engine enum member (its name, e.g. "C30")"""
    return member.name


def from_key[E: Enum](enum_type: type[E], key: str) -> E:
    """Return the engine enum member of a key

    Raises:
        KeyError: If the key is not a member name of enum_type.
    """
    return enum_type[key]


def cm_from_m(value_m: float) -> float:
    """Convert meters to centimeters"""
    return value_m * _CM_PER_M


def m_from_cm(value_cm: float) -> float:
    """Convert centimeters to meters"""
    return value_cm / _CM_PER_M
