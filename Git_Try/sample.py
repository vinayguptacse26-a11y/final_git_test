from utils import add

# Dummy comment added by automation for feature-test branch

def greet():
    print("Greetings, universe!")
    print("Hello, awesome world!")
    print("This line is intentionally changed to cause a merge conflict.")
    print("Testing merge conflicts with AI Git Push project!")
    print("hello from Vinay Gupta")
    print("hello from Gaurav")


def perform_calculation():
    # Expecting a dictionary return type now
    res = add(10.5, 20.3, 5.0, round_to=1)
    print(f"Calculation result: {res['total']} (from {res['count']} numbers)")

if __name__ == "__main__":
    greet()
    perform_calculation()
def greet():
    print("Greetings, universe!")
    print("Hello, awesome world!")
    print("This line is intentionally changed to cause a merge conflict.")
    print("Testing merge conflicts with AI Git Push project!")
    print("hello from Vinay Gupta")

<<<<<<< HEAD
def perform_calculation():
    # Expecting a dictionary return type now
    res = add(10.5, 20.3, 5.0, round_to=1)
    print(f"Calculation result: {res['total']} (from {res['count']} numbers)")
=======
>>>>>>> cd36c1f (chore: simplify add to two-arg signature)

def perform_calculation():
    # Updated to use the simplified add(a, b) signature
    try:
        result = add(10.5, 20.3)
        print(f"Calculation result: {result}")
    except Exception as exc:
        print(f"Calculation failed: {exc}")


def isprime(n: Any) -> bool:
    """Return True if n is a prime number.

    Accepts ints, floats that represent whole numbers, and numeric strings.
    Raises TypeError for inputs that cannot be interpreted as an integral value.

    Examples:
        isprime(7) -> True
        isprime("11") -> True
        isprime(4.0) -> False

    Note: booleans are not accepted (they subclass int but are not meaningful here).
    """
    logger.info("isprime() called with: %r", n)

    if n is None:
        raise TypeError("None is not a valid numeric value")

    # Reject booleans explicitly
    if isinstance(n, bool):
        raise TypeError("bool is not a valid input for isprime")

    # Determine integer value from input
    try:
        if isinstance(n, int):
            n_int = n
        elif isinstance(n, float):
            if not n.is_integer():
                raise TypeError(f"Non-integral float passed to isprime: {n!r}")
            n_int = int(n)
        else:
            # Try parsing strings or other types that have a reasonable int()
            s = str(n).strip()
            # Allow signs for integer strings
            if s.startswith(('+', '-')):
                sign = s[0]
                digits = s[1:]
                if not digits.isdigit():
                    raise TypeError(f"Unable to interpret input as integer: {n!r}")
            elif not s.isdigit():
                raise TypeError(f"Unable to interpret input as integer: {n!r}")
            n_int = int(s)
    except (ValueError, TypeError) as exc:
        logger.exception("Failed to interpret input as integer: %r", n)
        raise TypeError(f"Unable to interpret input as an integer: {n!r}") from exc

    # Quick checks
    if n_int < 2:
        return False
    if n_int in (2, 3):
        return True
    if n_int % 2 == 0 or n_int % 3 == 0:
        return False

    # Check wheel of 6k +/- 1
    i = 5
    while i * i <= n_int:
        if n_int % i == 0 or n_int % (i + 2) == 0:
            return False
        i += 6
    return True


if __name__ == "__main__":
    greet()
    perform_calculation()