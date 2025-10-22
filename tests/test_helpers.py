
import pytest
import math
from clases.helpers import parse_numeric

def test_parse_numeric_simple():
    assert parse_numeric("10.5") == 10.5

def test_parse_numeric_expression():
    assert parse_numeric("2 * 5") == 10.0

def test_parse_numeric_with_pi():
    assert parse_numeric("2 * pi") == 2 * math.pi

def test_parse_numeric_with_power():
    assert parse_numeric("2^3") == 8.0

def test_parse_numeric_invalid_expression():
    with pytest.raises(ValueError):
        parse_numeric("2 * x")

def test_parse_numeric_empty_string():
    with pytest.raises(ValueError):
        parse_numeric("")

def test_parse_numeric_unsafe_expression():
    with pytest.raises(Exception):
        parse_numeric("__import__('os').system('echo pwned')")
