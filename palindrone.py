"""
palindrone.py
Utility to check whether an integer is a palindrome.
"""

def is_palindrome_number(n: int) -> bool:
    """Return True if n is a palindrome integer, False otherwise.

    Handles negative numbers (not palindromes) and zero.
    This implementation does not convert the number to string — it uses
    numeric operations so it's suitable for very large integers without
    creating intermediate string objects.
    """
    if n < 0:
        return False
    # Single digit numbers are palindromes
    if n < 10:
        return True

    original = n
    reversed_num = 0
    while n > 0:
        reversed_num = reversed_num * 10 + (n % 10)
        n //= 10
    return original == reversed_num


def main():
    try:
        s = input("Enter an integer to check for palindrome: ")
        n = int(s.strip())
    except ValueError:
        print("Please enter a valid integer.")
        return

    if is_palindrome_number(n):
        print(f"{n} is a palindrome.")
    else:
        print(f"{n} is not a palindrome.")


if __name__ == "__main__":
    main()
