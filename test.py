"""Utilities for quick local testing.

This module provides a simple is_prime function for unit tests and quick checks.
"""

import math


def is_prime(n: int) -> bool:
    """Return True if n is a prime number, otherwise False.

    Args:
        n: Integer to test for primality.

    Examples:
        >>> is_prime(7)
        True
        >>> is_prime(8)
        False
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    limit = math.isqrt(n)
    i = 3
    while i <= limit:
        if n % i == 0:
            return False
        i += 2
    return True


if __name__ == "__main__":
    # Basic manual tests
    test_values = [0, 1, 2, 3, 4, 16, 17, 19, 20, 23, 29, 97, 100]
    for v in test_values:
        print(f"{v}: {'prime' if is_prime(v) else 'composite'}")
