from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    DOLLAR_VARIATION_COMPARISON_DAYS,
    DOLLAR_VARIATION_HISTORY_BUFFER_DAYS,
    SELIC_COMPARISON_WINDOW_DAYS,
    PeriodComparison,
    calculate_compound_accumulated_rate,
    calculate_dollar_variation_30_days,
    calculate_ipca_accumulated_12_months,
    calculate_selic_change_in_points,
    compare_to_previous_period,
)


def build_history(
    indicator_code: int,
    rows: list[tuple[date, float]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "indicator_code": [
                indicator_code for _ in rows
            ],
            "reference_date": [
                pd.Timestamp(reference_date)
                for reference_date, _ in rows
            ],
            "value": [value for _, value in rows],
        }
    )


def test_compare_to_previous_period_accepts_plain_date_objects():
    history = pd.DataFrame(
        {
            "indicator_code": [432, 432],
            "reference_date": [
                date(2026, 8, 24),
                date(2026, 9, 23),
            ],
            "value": [14.00, 15.25],
        }
    )

    comparison = compare_to_previous_period(
        history, days=30
    )

    assert comparison.current_value == 15.25
    assert comparison.previous_value == 14.00


def test_compare_to_previous_period_accepts_text_dates():
    history = pd.DataFrame(
        {
            "indicator_code": [432, 432],
            "reference_date": [
                "2026-08-24",
                "2026-09-23",
            ],
            "value": [14.00, 15.25],
        }
    )

    comparison = compare_to_previous_period(
        history, days=30
    )

    assert comparison.previous_date == date(2026, 8, 24)


def test_compare_to_previous_period_rejects_unparseable_dates():
    history = pd.DataFrame(
        {
            "indicator_code": [432, 432],
            "reference_date": [
                "não é uma data",
                "2026-09-23",
            ],
            "value": [14.00, 15.25],
        }
    )

    with pytest.raises(ValueError, match="datas inválidas"):
        compare_to_previous_period(history, days=30)


def test_compare_to_previous_period_rejects_non_numeric_values():
    history = pd.DataFrame(
        {
            "indicator_code": [432, 432],
            "reference_date": [
                date(2026, 8, 24),
                date(2026, 9, 23),
            ],
            "value": ["quatorze", 15.25],
        }
    )

    with pytest.raises(
        ValueError, match="não numéricos"
    ):
        compare_to_previous_period(history, days=30)


def test_compare_to_previous_period_rejects_mixed_indicators():
    history = pd.DataFrame(
        {
            "indicator_code": [432, 1],
            "reference_date": [
                date(2026, 8, 24),
                date(2026, 9, 23),
            ],
            "value": [14.00, 5.34],
        }
    )

    with pytest.raises(
        ValueError, match="mais de um indicador"
    ):
        compare_to_previous_period(history, days=30)


def test_compare_to_previous_period_rejects_missing_columns():
    history = pd.DataFrame(
        {
            "reference_date": [date(2026, 9, 23)],
            "value": [15.25],
        }
    )

    with pytest.raises(
        ValueError, match="colunas obrigatórias"
    ):
        compare_to_previous_period(history, days=30)


def test_compare_to_previous_period_rejects_empty_history():
    with pytest.raises(ValueError, match="vazio"):
        compare_to_previous_period(pd.DataFrame())


def test_compare_to_previous_period_uses_nearest_prior_value():
    history = build_history(
        432,
        [
            (date(2026, 8, 20), 13.75),
            (date(2026, 8, 24), 14.00),
            (date(2026, 9, 23), 15.25),
        ],
    )

    comparison = compare_to_previous_period(
        history, days=30
    )

    assert comparison == PeriodComparison(
        indicator_code=432,
        current_date=date(2026, 9, 23),
        current_value=15.25,
        previous_date=date(2026, 8, 24),
        previous_value=14.00,
        absolute_change=pytest.approx(1.25),
        percentage_change=pytest.approx(8.928571, rel=1e-6),
    )


def test_compare_to_previous_period_rejects_non_positive_window():
    history = build_history(
        432, [(date(2026, 9, 23), 15.25)]
    )

    with pytest.raises(
        ValueError, match="janela de comparação"
    ):
        compare_to_previous_period(history, days=0)


def test_compare_to_previous_period_rejects_when_no_prior_data():
    history = build_history(
        432, [(date(2026, 9, 23), 15.25)]
    )

    with pytest.raises(
        ValueError, match="Não há valores disponíveis"
    ):
        compare_to_previous_period(history, days=30)


def test_compare_to_previous_period_rejects_zero_previous_value():
    history = build_history(
        1,
        [
            (date(2026, 8, 24), 0.0),
            (date(2026, 9, 23), 5.34),
        ],
    )

    with pytest.raises(
        ValueError, match="valor anterior igual a zero"
    ):
        compare_to_previous_period(history, days=30)


def test_dollar_history_buffer_is_wider_than_the_comparison_window():
    assert DOLLAR_VARIATION_COMPARISON_DAYS == 30
    assert DOLLAR_VARIATION_HISTORY_BUFFER_DAYS >= 37
    assert (
        DOLLAR_VARIATION_HISTORY_BUFFER_DAYS
        > DOLLAR_VARIATION_COMPARISON_DAYS
    )


def test_calculate_dollar_variation_compares_against_30_days_not_37():
    history = build_history(
        1,
        [
            (date(2026, 8, 10), 5.00),
            (date(2026, 8, 20), 5.10),
            (date(2026, 9, 23), 5.25),
        ],
    )

    variation = calculate_dollar_variation_30_days(history)

    assert variation == pytest.approx(
        2.941176, rel=1e-6
    )


def test_calculate_dollar_variation_finds_friday_when_30_days_ago_is_sunday():
    current_date = date(2026, 9, 22)
    thirty_days_ago = date(2026, 8, 23)
    assert thirty_days_ago.strftime("%A") == "Sunday"

    previous_friday = date(2026, 8, 21)
    assert previous_friday.strftime("%A") == "Friday"

    history_start = current_date - timedelta(
        days=DOLLAR_VARIATION_HISTORY_BUFFER_DAYS
    )
    assert previous_friday >= history_start

    history = build_history(
        1,
        [
            (previous_friday, 5.00),
            (current_date, 5.25),
        ],
    )

    comparison = compare_to_previous_period(
        history, days=DOLLAR_VARIATION_COMPARISON_DAYS
    )

    assert comparison.previous_date == previous_friday
    assert comparison.percentage_change == pytest.approx(
        5.0
    )


def test_calculate_selic_change_defaults_to_twelve_months():
    assert SELIC_COMPARISON_WINDOW_DAYS == 365

    history = build_history(
        432,
        [
            (date(2025, 9, 20), 15.00),
            (date(2026, 3, 1), 14.75),
            (date(2026, 9, 23), 14.75),
        ],
    )

    change = calculate_selic_change_in_points(history)

    assert change == pytest.approx(-0.25)


def test_calculate_selic_change_in_points_accepts_custom_window():
    history = build_history(
        432,
        [
            (date(2026, 8, 24), 15.00),
            (date(2026, 9, 23), 14.75),
        ],
    )

    change = calculate_selic_change_in_points(
        history, days=30
    )

    assert change == pytest.approx(-0.25)


def test_calculate_compound_accumulated_rate_is_multiplicative_not_additive():
    monthly_rates = [1.0] * 12

    accumulated = calculate_compound_accumulated_rate(
        monthly_rates
    )

    assert accumulated == pytest.approx(12.682503, rel=1e-6)
    assert accumulated != pytest.approx(12.0)


@pytest.mark.parametrize(
    "monthly_rates",
    [
        [1.0] * 12,
        np.array([1.0] * 12),
        pd.Series([1.0] * 12),
    ],
)
def test_calculate_compound_accumulated_rate_accepts_array_like_inputs(
    monthly_rates,
):
    accumulated = calculate_compound_accumulated_rate(
        monthly_rates
    )

    assert accumulated == pytest.approx(12.682503, rel=1e-6)


def test_calculate_compound_accumulated_rate_rejects_empty_series():
    with pytest.raises(
        ValueError, match="ao menos uma taxa"
    ):
        calculate_compound_accumulated_rate(
            np.array([], dtype="float64")
        )


def test_calculate_compound_accumulated_rate_rejects_missing_values():
    with pytest.raises(
        ValueError, match="ausentes ou inválidos"
    ):
        calculate_compound_accumulated_rate(
            [0.5, float("nan"), 0.4]
        )


def test_calculate_compound_accumulated_rate_rejects_rate_at_or_below_negative_100():
    with pytest.raises(
        ValueError, match="cálculo composto inválido"
    ):
        calculate_compound_accumulated_rate(
            [0.5, -100.0, 0.4]
        )


def test_calculate_ipca_accumulated_12_months_uses_compound_interest():
    monthly_rates = [
        0.50, 0.44, 0.30, -0.10, 0.60, 0.70,
        0.20, 0.10, 0.35, 0.55, 0.45, 0.40,
    ]

    monthly_dates = pd.date_range(
        start="2025-10-01", periods=12, freq="MS"
    )

    history = build_history(
        433,
        list(zip(monthly_dates.date, monthly_rates)),
    )

    accumulated = calculate_ipca_accumulated_12_months(
        history
    )

    expected_factor = 1.0
    for rate in monthly_rates:
        expected_factor *= 1 + (rate / 100)

    expected_accumulated = (expected_factor - 1) * 100

    assert accumulated == pytest.approx(
        expected_accumulated
    )
    assert accumulated != pytest.approx(
        sum(monthly_rates)
    )


def test_calculate_ipca_accumulated_12_months_requires_twelve_readings():
    history = build_history(
        433,
        [
            (date(2026, month, 1), 0.4)
            for month in range(1, 6)
        ],
    )

    with pytest.raises(
        ValueError, match="ao menos 12 meses"
    ):
        calculate_ipca_accumulated_12_months(history)


def test_calculate_ipca_accumulated_12_months_uses_last_twelve_readings_only():
    older_month = [(date(2024, 12, 1), 100.0)]

    monthly_rates = [0.5] * 12

    monthly_dates = pd.date_range(
        start="2025-01-01", periods=12, freq="MS"
    )

    history = build_history(
        433,
        older_month
        + list(zip(monthly_dates.date, monthly_rates)),
    )

    accumulated = calculate_ipca_accumulated_12_months(
        history
    )

    expected_factor = 1.0
    for rate in monthly_rates:
        expected_factor *= 1 + (rate / 100)

    expected_accumulated = (expected_factor - 1) * 100

    assert accumulated == pytest.approx(
        expected_accumulated
    )


def test_calculate_ipca_accumulated_12_months_rejects_non_consecutive_months():
    monthly_dates = list(
        pd.date_range(
            start="2025-10-01", periods=11, freq="MS"
        ).date
    )

    monthly_dates.append(date(2026, 11, 1))

    history = build_history(
        433,
        list(zip(monthly_dates, [0.4] * 12)),
    )

    with pytest.raises(
        ValueError, match="meses consecutivos"
    ):
        calculate_ipca_accumulated_12_months(history)
