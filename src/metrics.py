from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

IPCA_ACCUMULATION_MONTHS = 12

SELIC_COMPARISON_WINDOW_DAYS = 365

DOLLAR_VARIATION_COMPARISON_DAYS = 30

DOLLAR_VARIATION_HISTORY_BUFFER_DAYS = 37

DEFAULT_COMPARISON_WINDOW_DAYS = 30

REQUIRED_HISTORY_COLUMNS = {
    "indicator_code",
    "reference_date",
    "value",
}


@dataclass(frozen=True)
class PeriodComparison:
    indicator_code: int
    current_date: date
    current_value: float
    previous_date: date
    previous_value: float
    absolute_change: float
    percentage_change: float


def _normalize_history(history: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(history, pd.DataFrame) or history.empty:
        raise ValueError(
            "O histórico do indicador está vazio."
        )

    missing_columns = (
        REQUIRED_HISTORY_COLUMNS - set(history.columns)
    )

    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(
            "O histórico do indicador não possui as "
            f"colunas obrigatórias: {columns}."
        )

    normalized = history.copy()

    try:
        normalized["reference_date"] = pd.to_datetime(
            normalized["reference_date"],
            format="mixed",
        )
    except (ValueError, TypeError) as error:
        raise ValueError(
            "A coluna 'reference_date' contém datas "
            "inválidas."
        ) from error

    if normalized["reference_date"].isna().any():
        raise ValueError(
            "A coluna 'reference_date' contém datas "
            "ausentes ou inválidas."
        )

    normalized["value"] = pd.to_numeric(
        normalized["value"], errors="coerce"
    )

    if normalized["value"].isna().any():
        raise ValueError(
            "A coluna 'value' contém valores ausentes ou "
            "não numéricos."
        )

    if not np.isfinite(normalized["value"]).all():
        raise ValueError(
            "A coluna 'value' contém valores não finitos."
        )

    if normalized["indicator_code"].nunique() > 1:
        raise ValueError(
            "O histórico contém mais de um indicador "
            "misturado; informe o histórico de um único "
            "indicador por vez."
        )

    return normalized.sort_values(
        "reference_date"
    ).reset_index(drop=True)


def _latest_value_on_or_before(
    history: pd.DataFrame,
    target_date: pd.Timestamp,
) -> tuple[date, float]:
    eligible_rows = history[
        history["reference_date"] <= target_date
    ]

    if eligible_rows.empty:
        raise ValueError(
            "Não há valores disponíveis em ou antes de "
            f"{target_date:%d/%m/%Y}."
        )

    last_row = eligible_rows.iloc[-1]

    return (
        last_row["reference_date"].date(),
        float(last_row["value"]),
    )


def compare_to_previous_period(
    history: pd.DataFrame,
    days: int = DEFAULT_COMPARISON_WINDOW_DAYS,
) -> PeriodComparison:
    if days <= 0:
        raise ValueError(
            "A janela de comparação deve ser positiva."
        )

    normalized_history = _normalize_history(history)

    current_row = normalized_history.iloc[-1]
    current_date = current_row["reference_date"].date()
    current_value = float(current_row["value"])

    target_date = pd.Timestamp(
        current_date - timedelta(days=days)
    )

    previous_date, previous_value = (
        _latest_value_on_or_before(
            normalized_history, target_date
        )
    )

    if previous_value == 0:
        raise ValueError(
            "Não é possível calcular a variação percentual "
            "a partir de um valor anterior igual a zero."
        )

    absolute_change = current_value - previous_value

    percentage_change = (
        (current_value / previous_value) - 1
    ) * 100

    return PeriodComparison(
        indicator_code=int(
            current_row["indicator_code"]
        ),
        current_date=current_date,
        current_value=current_value,
        previous_date=previous_date,
        previous_value=previous_value,
        absolute_change=absolute_change,
        percentage_change=percentage_change,
    )


def calculate_dollar_variation_30_days(
    history: pd.DataFrame,
) -> float:
    comparison = compare_to_previous_period(
        history, days=DOLLAR_VARIATION_COMPARISON_DAYS
    )

    return comparison.percentage_change


def calculate_selic_change_in_points(
    history: pd.DataFrame,
    days: int = SELIC_COMPARISON_WINDOW_DAYS,
) -> float:
    comparison = compare_to_previous_period(
        history, days=days
    )

    return comparison.absolute_change


def calculate_compound_accumulated_rate(
    monthly_rates_percent: Sequence[float],
) -> float:
    rates = pd.Series(
        monthly_rates_percent, dtype="float64"
    )

    if rates.empty:
        raise ValueError(
            "É necessário informar ao menos uma taxa "
            "mensal."
        )

    if rates.isna().any():
        raise ValueError(
            "As taxas mensais não podem conter valores "
            "ausentes ou inválidos."
        )

    if not np.isfinite(rates).all():
        raise ValueError(
            "As taxas mensais devem ser valores finitos."
        )

    growth_factors = 1 + (rates / 100)

    if (growth_factors <= 0).any():
        raise ValueError(
            "Uma taxa mensal menor ou igual a -100% torna "
            "o cálculo composto inválido."
        )

    accumulated_factor = growth_factors.prod()

    return (accumulated_factor - 1) * 100


def _validate_consecutive_months(
    reference_dates: pd.Series,
) -> None:
    month_indexes = (
        reference_dates.dt.year * 12
        + reference_dates.dt.month
    )

    month_steps = month_indexes.diff().dropna()

    if not (month_steps == 1).all():
        raise ValueError(
            "O histórico do IPCA deve conter 12 meses "
            "consecutivos, sem lacunas, para calcular o "
            "acumulado."
        )


def calculate_ipca_accumulated_12_months(
    history: pd.DataFrame,
) -> float:
    normalized_history = _normalize_history(history)

    if len(normalized_history) < IPCA_ACCUMULATION_MONTHS:
        raise ValueError(
            "São necessários ao menos 12 meses de "
            "histórico do IPCA para calcular o acumulado "
            f"(há {len(normalized_history)})."
        )

    last_twelve_months = normalized_history.tail(
        IPCA_ACCUMULATION_MONTHS
    )

    _validate_consecutive_months(
        last_twelve_months["reference_date"]
    )

    monthly_rates = last_twelve_months["value"].to_numpy()

    return calculate_compound_accumulated_rate(
        monthly_rates
    )
