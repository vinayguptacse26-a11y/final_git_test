def is_palindrome_number(n: int) -> bool:
    """Return True if n is a palindrome number.

    Negative numbers are not considered palindromes (by convention).
    """
    if n < 0:
        return False
    s = str(n)
    return s == s[::-1]


if __name__ == "__main__":
    # Simple CLI to check a number
    try:
        val = input("Enter an integer to check if it's a palindrome: ").strip()
        n = int(val)
    except (ValueError, EOFError):
        print("Invalid input. Please enter a valid integer.")
    else:
        if is_palindrome_number(n):
            print(f"{n} is a palindrome.")
        else:
            print(f"{n} is not a palindrome.")
