# NOTE: calculator1.py is retained for compatibility. Prefer using the primary calculator module.

"""
Calculator utilities (single authoritative implementation).
Both functions perform simple type-checking and always return floats.
"""

from typing import Union

Number = Union[int, float]

def _to_number(x: object) -> float:
    if isinstance(x, (int, float)):
        return float(x)
    raise TypeError(f"Unsupported operand type: {type(x).__name__}")

def add(a: Number, b: Number) -> float:
    """Return the sum of a and b as a float."""
    return _to_number(a) + _to_number(b)

def subtract(a: Number, b: Number) -> float:
    """Return the difference a - b as a float."""
    return _to_number(a) - _to_number(b)

def divide(a, b):
    """Return a / b with basic type checks and zero-division handling."""
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        raise TypeError('Both arguments must be int or float')
    if b == 0:
        raise ZeroDivisionError('division by zero')
    return a / b
