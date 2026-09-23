from datetime import date
import pytest
from src.run_etl import (
    calculate_historical_start_date,
    determine_start_date,
)

def test_calculates_five_year_historical_period() -> None:
    end_date = date(2026, 9, 23)

    result = calculate_historical_start_date(
        end_date
    )

    assert result == date(2021, 9, 23)


def test_handles_leap_day_in_historical_period() -> None:
    end_date = date(2024, 2, 29)

    result = calculate_historical_start_date(
        end_date
    )

    assert result == date(2019, 2, 28)


def test_backfill_does_not_query_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_database_query(
        indicator_code: int,
    ) -> None:
        pytest.fail(
            "O modo backfill não deveria consultar a última data."
        )

    monkeypatch.setattr(
        "src.run_etl.get_latest_reference_date",
        unexpected_database_query,
    )

    result = determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=True,
    )

    assert result == date(2021, 9, 23)


def test_uses_historical_period_when_database_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.run_etl.get_latest_reference_date",
        lambda indicator_code: None,
    )

    result = determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=False,
    )

    assert result == date(2021, 9, 23)


def test_reprocesses_last_seven_stored_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.run_etl.get_latest_reference_date",
        lambda indicator_code: date(2026, 9, 23),
    )

    result = determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=False,
    )

    assert result == date(2026, 9, 17)


def test_rejects_latest_date_in_the_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.run_etl.get_latest_reference_date",
        lambda indicator_code: date(2026, 9, 24),
    )

    with pytest.raises(
        RuntimeError,
        match="está no futuro",
    ):
        determine_start_date(
            indicator_code=432,
            end_date=date(2026, 9, 23),
            backfill=False,
        )

def test_determine_start_date_uses_custom_reprocess_window(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.run_etl.get_latest_reference_date",
        lambda indicator_code: date(2026, 9, 1),
    )

    start_date = determine_start_date(
        indicator_code=433,
        end_date=date(2026, 9, 23),
        backfill=False,
        reprocess_days=90,
    )

    assert start_date == date(2026, 6, 4)