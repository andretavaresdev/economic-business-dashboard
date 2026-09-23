import pytest

from src.audit import start_etl_execution

@pytest.mark.parametrize(
    "indicator_code",
    [0, -1, -432],
)
def test_start_etl_execution_rejects_invalid_indicator_code(
    indicator_code,
):
    with pytest.raises(
        ValueError,
        match="deve ser positivo",
    ):
        start_etl_execution(indicator_code)