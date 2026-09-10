import logging
from typing import Any

logger = logging.getLogger(__name__)


def add(a: Any, b: Any) -> float:
    """Add exactly two numeric values and return their sum as a float.

    This simplified version accepts two positional arguments only. It attempts to
    coerce inputs to float (accepting ints, floats, and numeric strings). If a
    value is None or cannot be converted to float, a TypeError is raised.
    No external packages are used.
    """
    logger.info("add() called with: %r, %r", a, b)

    if a is None or b is None:
        raise TypeError("None is not a valid numeric value")

    try:
        return float(a) + float(b)
    except Exception as exc:
        logger.exception("Failed to add numbers: %r, %r", a, b)
        # Re-raise a clearer TypeError for callers
        raise TypeError(f"Unable to convert inputs to numbers: {a!r}, {b!r}") from exc


def sub(a: Any, b: Any) -> float:
    """Subtract b from a. Coerces inputs to floats when possible."""
    a_f = float(a)
    b_f = float(b)
    return a_f - b_f


def multi(a: Any, b: Any) -> float:
    """Multiply two values. Coerces to float."""
    a_f = float(a)
    b_f = float(b)
    return a_f * b_f


def divide(a: Any, b: Any) -> float:
    """Divide a by b. Raises ZeroDivisionError for division by zero (caller can handle).

    Coerces inputs to floats.
    """
    a_f = float(a)
    b_f = float(b)
    if b_f == 0:
        raise ZeroDivisionError("division by zero")
    return a_f / b_f


# Dummy comment added by automation for feature-test branch

def greet():
    print("Greetings, universe!")
    print("Hello, awesome world!")
    print("This line is intentionally changed to cause a merge conflict.")
    print("Testing merge conflicts with AI Git Push project!")
    print("hello from emesh")
    print("hello from Vinay Gupta")


def perform_calculation():
    # Updated to use the simplified add(a, b) signature
    try:
        result = add(10.5, 20.3)
        print(f"Calculation result: {result}")
    except Exception as exc:
        print(f"Calculation failed: {exc}")


if __name__ == "__main__":
    greet()
    perform_calculation()
