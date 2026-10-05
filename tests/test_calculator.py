import math
import pytest
from calculator import add, subtract

def test_add_integers_and_floats():
    assert add(1, 2) == 3.0
    assert add(1.5, 2.25) == pytest.approx(3.75)

def test_subtract_integers_and_floats():
    assert subtract(5, 3) == 2.0
    assert subtract(5.5, 2.25) == pytest.approx(3.25)

def test_add_invalid_types_raise_type_error():
    with pytest.raises(TypeError):
        add("1", 2)
    with pytest.raises(TypeError):
        add(None, 2)

def test_subtract_invalid_types_raise_type_error():
    with pytest.raises(TypeError):
        subtract([], 1)
    with pytest.raises(TypeError):
        subtract(1, {})

def test_edge_cases_large_numbers_and_nan():
    # large numbers
    large = 10**18
    assert add(large, large) == float(large + large)
    # NaN handling - math.isnan on the result
    nan = float("nan")
    res = add(nan, 1.0)
    assert math.isnan(res)
