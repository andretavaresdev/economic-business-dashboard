import pytest

from src.indicators import INDICATORS, get_indicator

def test_catalog_contains_expected_indicators():
    assert set(INDICATORS) == {"selic", "ipca", "dolar"}

@pytest.mark.parametrize(
    ("indicator_name", "expected_code"),
    [
        ("selic", 432),
        ("ipca", 433),
        ("dolar", 1),
    ],
)
def test_get_indicator_returns_correct_code(
    indicator_name,
    expected_code,
):
    indicator = get_indicator(indicator_name)

    assert indicator.code == expected_code


def test_get_indicator_normalizes_input():
    indicator = get_indicator("  SELIC  ")

    assert indicator.code == 432

def test_get_indicator_rejects_unknown_indicator():
    with pytest.raises(ValueError, match="não encontrado"):
        get_indicator("desemprego")