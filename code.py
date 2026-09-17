#!/usr/bin/env python3
"""
A safe, full-featured calculator REPL supporting arithmetic, power, modulus,
floor division, factorial, roots, percentages and many math functions.

Usage:
- Run: python code.py
- Type expressions like: 2+3*4, (2+3)/5, 2**8, 10//3, 7%3
- Use math functions: sin(pi/2), sqrt(2), factorial(5), log(10), exp(1)
- Constants: pi, e
- To exit: type 'exit' or 'quit' or press Ctrl+C

This evaluator is intentionally restrictive: it parses expressions with
ast and only allows a safe subset of nodes and a curated set of math
functions/constants.
"""

import ast
import operator as op
import math
import sys

# Supported binary operators
_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

# Supported unary operators
_UNARY_OPS = {
    ast.UAdd: lambda x: x,
    ast.USub: op.neg,
}

# Allowed functions from the math module and builtins we deem safe
_ALLOWED_FUNCS = {
    # Trigonometry
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    # Exponentials / logs
    'exp': math.exp,
    'log': math.log,      # natural log; log(x, base) also supported via second arg
    'log10': math.log10,
    # Roots / powers
    'sqrt': math.sqrt,
    'pow': pow,
    # Utilities
    'abs': abs,
    'round': round,
    'factorial': math.factorial,
    'floor': math.floor,
    'ceil': math.ceil,
    'degrees': math.degrees,
    'radians': math.radians,
    # min/max
    'min': min,
    'max': max,
}

# Allowed constants
_ALLOWED_NAMES = {
    'pi': math.pi,
    'e': math.e,
}


class EvalError(Exception):
    pass


def _eval(node):
    """Recursively evaluate an AST node in a safe manner."""
    if isinstance(node, ast.Expression):
        return _eval(node.body)

    if isinstance(node, ast.Constant):
        # ast.Constant covers numbers in Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise EvalError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Num):  # for older Python AST
        return node.n

    if isinstance(node, ast.BinOp):
        left = _eval(node.left)
        right = _eval(node.right)
        op_type = type(node.op)
        if op_type in _BIN_OPS:
            try:
                return _BIN_OPS[op_type](left, right)
            except ZeroDivisionError:
                raise EvalError("Division by zero")
        raise EvalError(f"Unsupported binary operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand)
        op_type = type(node.op)
        if op_type in _UNARY_OPS:
            return _UNARY_OPS[op_type](operand)
        raise EvalError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.Call):
        # Only allow simple function calls like func(arg1, arg2, ...)
        if not isinstance(node.func, ast.Name):
            raise EvalError("Only direct function calls are allowed")
        func_name = node.func.id
        if func_name not in _ALLOWED_FUNCS:
            raise EvalError(f"Function '{func_name}' is not allowed")
        func = _ALLOWED_FUNCS[func_name]

        # Evaluate args
        args = [_eval(arg) for arg in node.args]
        # No keywords allowed for simplicity and safety
        if node.keywords:
            raise EvalError("Keyword arguments are not allowed")

        # Special handling: factorial requires integer >= 0
        if func_name == 'factorial':
            if len(args) != 1:
                raise EvalError("factorial() takes exactly one argument")
            n = args[0]
            if not (isinstance(n, int) or (isinstance(n, float) and n.is_integer())):
                raise EvalError("factorial() only accepts integer values")
            n = int(n)
            if n < 0:
                raise EvalError("factorial() not defined for negative values")
            return func(n)

        try:
            return func(*args)
        except Exception as ex:
            raise EvalError(f"Error calling function '{func_name}': {ex}")

    if isinstance(node, ast.Name):
        name = node.id
        if name in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[name]
        # allow 'pi', 'e' only; also allow boolean-like names? not necessary
        raise EvalError(f"Name '{name}' is not defined")

    if isinstance(node, ast.Tuple):
        return tuple(_eval(elt) for elt in node.elts)

    # Disallow everything else (comprehensions, attributes, subscripts, etc.)
    raise EvalError(f"Unsupported expression: {type(node).__name__}")


def safe_eval(expr: str):
    """Safely evaluate a math expression string and return the result.

    This function parses the expression into an AST and evaluates only a
    safe subset of nodes. It prevents access to globals, attributes,
    imports, and other unsafe constructs.
    """
    try:
        parsed = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise EvalError(f"Syntax error: {e}")

    # Walk the AST to ensure there are no unsafe nodes quickly (defense in depth)
    for node in ast.walk(parsed):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Lambda, ast.Attribute,
                             ast.Subscript, ast.Assign, ast.AugAssign, ast.Delete,
                             ast.For, ast.While, ast.If, ast.With, ast.Try, ast.ClassDef,
                             ast.FunctionDef, ast.ListComp, ast.SetComp, ast.DictComp,
                             ast.GeneratorExp, ast.Yield, ast.YieldFrom)):
            raise EvalError(f"Disallowed expression type: {type(node).__name__}")

    return _eval(parsed)


def cube(n):
    """Return the cube of n."""
    return n ** 3

# Register cube in the allowed functions so safe_eval can call it
_ALLOWED_FUNCS['cube'] = cube


def _print_welcome():
    print("Simple Safe Calculator")
    print("Type arithmetic expressions to evaluate. Examples:")
    print("  2 + 3 * 4")
    print("  (2 + 3) / 5")
    print("  2**8, 10//3, 7%3")
    print("  sqrt(2), sin(pi/2), factorial(5), log(10)")
    print("Constants available: pi, e")
    print("Type 'help' to list available functions, 'exit' or 'quit' to leave.")


def _print_help():
    print("Available functions:")
    names =[REDACTED]
    print(', '.join(names))


def repl():
    _print_welcome()
    while True:
        try:
            expr = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nGoodbye!')
            return

        if not expr:
            continue
        if expr.lower() in ('exit', 'quit'):
            print('Goodbye!')
            return
        if expr.lower() == 'help':
            _print_help()
            continue

        try:
            result = safe_eval(expr)
            print(result)
        except EvalError as ee:
            print('Error:', ee)
        except Exception as ex:
            print('Unexpected error:', ex)


if __name__ == '__main__':
    repl()
