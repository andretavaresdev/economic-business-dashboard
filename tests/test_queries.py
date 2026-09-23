from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from src.queries import (
    get_indicator_history,
    normalize_indicator_data,
)


def test_normalize_indicator_data_converts_types():
    original_dataframe = pd.DataFrame(
        {
            "reference_date": [
                date(2026, 9, 23),
            ],
            "value": [
                Decimal("14.25"),
            ],
        }
    )

    normalized_dataframe = normalize_indicator_data(
        original_dataframe
    )

    assert pd.api.types.is_datetime64_any_dtype(
        normalized_dataframe["reference_date"]
    )
    assert normalized_dataframe.loc[0, "value"] == 14.25

    assert original_dataframe.loc[
        0, "value"
    ] == Decimal("14.25")


@pytest.mark.parametrize(
    "indicator_code",
    [0, -1],
)
def test_get_indicator_history_rejects_invalid_code(
    indicator_code,
):
    with pytest.raises(
        ValueError,
        match="deve ser positivo",
    ):
        get_indicator_history(indicator_code)


def test_get_indicator_history_rejects_invalid_period():
    with pytest.raises(
        ValueError,
        match="data inicial",
    ):
        get_indicator_history(
            indicator_code=432,
            start_date=date(2026, 9, 23),
            end_date=date(2026, 9, 1),
        )

def test_get_indicator_history_builds_date_filters(
    monkeypatch,
):
    captured_arguments = {}

    def fake_execute_query(
        query,
        parameters=(),
    ):
        captured_arguments["query"] = query
        captured_arguments["parameters"] = parameters

        return pd.DataFrame(
            {
                "indicator_code": [432],
                "indicator_name": ["Selic"],
                "unit": ["% ao ano"],
                "frequency": ["diária"],
                "reference_date": [
                    date(2026, 9, 1),
                ],
                "value": [
                    Decimal("14.00"),
                ],
            }
        )

    monkeypatch.setattr(
        "src.queries.execute_query",
        fake_execute_query,
    )

    result = get_indicator_history(
        indicator_code=432,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 9, 23),
    )

    assert captured_arguments["parameters"] == [
        432,
        date(2026, 1, 1),
        date(2026, 9, 23),
    ]

    assert "v.data_referencia >= %s" in (
        captured_arguments["query"]
    )
    assert "v.data_referencia <= %s" in (
        captured_arguments["query"]
    )

    assert result.loc[0, "value"] == 14.0