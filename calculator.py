"""Simple calculator helpers.

This module provides a minimal add() function used by the test suite.
"""

def add(a, b):
    """Return the sum of two numeric values as a float.

    Only int and float types are accepted. Passing other types (like str,
    None, list, dict) raises TypeError so callers can't accidentally
    rely on coercion.
    """
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be int or float")
    return float(a) + float(b)

def subtract(a, b):
    """Return a - b with the same type checks as add."""
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        raise TypeError('Both arguments must be int or float')
    return a - b

