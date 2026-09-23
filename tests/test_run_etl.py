from datetime import date

import pytest

import src.run_etl as run_etl


def test_calculates_five_year_historical_period() -> None:
    end_date = date(2026, 9, 23)

    result = run_etl.calculate_historical_start_date(
        end_date
    )

    assert result == date(2021, 9, 23)


def test_handles_leap_day_in_historical_period() -> None:
    end_date = date(2024, 2, 29)

    result = run_etl.calculate_historical_start_date(
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
        run_etl,
        "get_latest_reference_date",
        unexpected_database_query,
    )

    result = run_etl.determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=True,
    )

    assert result == date(2021, 9, 23)


def test_uses_historical_period_when_database_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_etl,
        "get_latest_reference_date",
        lambda indicator_code: None,
    )

    result = run_etl.determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=False,
    )

    assert result == date(2021, 9, 23)


def test_reprocesses_last_seven_stored_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_etl,
        "get_latest_reference_date",
        lambda indicator_code: date(2026, 9, 23),
    )

    result = run_etl.determine_start_date(
        indicator_code=432,
        end_date=date(2026, 9, 23),
        backfill=False,
    )

    assert result == date(2026, 9, 17)


def test_rejects_latest_date_in_the_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_etl,
        "get_latest_reference_date",
        lambda indicator_code: date(2026, 9, 24),
    )

    with pytest.raises(
        RuntimeError,
        match="está no futuro",
    ):
        run_etl.determine_start_date(
            indicator_code=432,
            end_date=date(2026, 9, 23),
            backfill=False,
        )