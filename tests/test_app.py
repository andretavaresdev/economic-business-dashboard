from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app import (
    format_indicator_value,
    format_number_br,
    indicator_value_axis_label,
)

APP_PATH = str(
    Path(__file__).resolve().parent.parent / "app.py"
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def build_latest_values() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "indicator_code": 1,
                "indicator_name": "Dólar comercial",
                "unit": "R$/US$",
                "frequency": "diária",
                "reference_date": pd.Timestamp(2026, 9, 23),
                "value": 5.3421,
            },
            {
                "indicator_code": 433,
                "indicator_name": "IPCA",
                "unit": "% ao mês",
                "frequency": "mensal",
                "reference_date": pd.Timestamp(2026, 9, 23),
                "value": 0.44,
            },
            {
                "indicator_code": 432,
                "indicator_name": "Selic",
                "unit": "% ao ano",
                "frequency": "diária",
                "reference_date": pd.Timestamp(2026, 9, 23),
                "value": 15.25,
            },
        ]
    )


def build_history(
    indicator_code: int,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    reference_dates = pd.date_range(
        start=start_date, end=end_date, periods=5
    )

    return pd.DataFrame(
        {
            "indicator_code": indicator_code,
            "indicator_name": "Indicador",
            "unit": "unidade",
            "frequency": "diária",
            "reference_date": reference_dates,
            "value": [
                float(indicator_code) + step
                for step in range(len(reference_dates))
            ],
        }
    )


class HistorySpy:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(
        self,
        indicator_code: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        self.calls.append(
            {
                "indicator_code": indicator_code,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        return build_history(
            indicator_code, start_date, end_date
        )


def run_app(monkeypatch, history_spy=None, latest_values=None):
    if latest_values is None:
        latest_values = build_latest_values()

    if history_spy is None:
        history_spy = HistorySpy()

    monkeypatch.setattr(
        "src.queries.get_latest_indicator_values",
        lambda: latest_values,
    )
    monkeypatch.setattr(
        "src.queries.get_indicator_history",
        history_spy,
    )

    at = AppTest.from_file(APP_PATH)
    at.run()

    return at, history_spy


def test_format_number_br_uses_brazilian_thousands_and_decimal():
    assert format_number_br(1234.5) == "1.234,50"
    assert format_number_br(0.44, 2) == "0,44"


def test_format_indicator_value_selic_and_ipca_are_percentual():
    assert format_indicator_value(432, 15.25) == "15,25%"
    assert format_indicator_value(433, 0.44) == "0,44%"


def test_format_indicator_value_dolar_is_reais():
    assert (
        format_indicator_value(1, 5.3421) == "R$ 5,3421"
    )


def test_indicator_value_axis_label_matches_unit():
    assert indicator_value_axis_label(1) == "Valor (R$)"
    assert indicator_value_axis_label(432) == "Valor (%)"


def test_renders_three_indicator_cards_with_correct_format(
    monkeypatch,
):
    at, _ = run_app(monkeypatch)

    assert at.exception == []

    metric_values = {
        metric.label: metric.value for metric in at.metric
    }

    assert "R$ 5,3421" in metric_values["💵 Dólar comercial"]
    assert metric_values["🛒 IPCA"] == "0,44%"
    assert metric_values["🏦 Selic"] == "15,25%"


def test_can_switch_selected_indicator_and_history_updates(
    monkeypatch,
):
    at, history_spy = run_app(monkeypatch)

    assert history_spy.calls[-1]["indicator_code"] == 1

    at.sidebar.selectbox[0].set_value("Selic").run()

    assert history_spy.calls[-1]["indicator_code"] == 432
    assert "Selic" in at.subheader[0].value


def test_can_switch_period_and_history_range_changes(
    monkeypatch,
):
    at, history_spy = run_app(monkeypatch)

    first_call = history_spy.calls[-1]
    assert (
        first_call["end_date"] - first_call["start_date"]
    ).days == 365

    at.sidebar.selectbox[1].set_value(
        "Últimos 5 anos"
    ).run()

    last_call = history_spy.calls[-1]
    assert (
        last_call["end_date"] - last_call["start_date"]
    ).days == 365 * 5


def test_visualizar_dados_shows_history_table(monkeypatch):
    at, _ = run_app(monkeypatch)

    assert len(at.dataframe) == 1

    table = at.dataframe[0].value

    assert len(table) == 5
    assert list(table.columns)[0] == "Data"


def test_shows_warning_when_no_indicators_available(
    monkeypatch,
):
    at, _ = run_app(
        monkeypatch,
        latest_values=pd.DataFrame(),
    )

    assert len(at.warning) == 1
    assert len(at.metric) == 0


def test_shows_error_when_database_is_unreachable(
    monkeypatch,
):
    def raise_connection_error():
        raise RuntimeError("conexão recusada")

    monkeypatch.setattr(
        "src.queries.get_latest_indicator_values",
        raise_connection_error,
    )

    at = AppTest.from_file(APP_PATH)
    at.run()

    assert len(at.error) == 1
    assert len(at.exception) == 1


def test_shows_info_when_history_is_empty_for_period(
    monkeypatch,
):
    at, _ = run_app(
        monkeypatch,
        history_spy=lambda **kwargs: pd.DataFrame(),
    )

    assert len(at.info) == 1
    assert len(at.dataframe) == 0


def rich_history_spy(
    indicator_code: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if indicator_code == 433:
        monthly_dates = pd.date_range(
            end="2026-09-01", periods=12, freq="MS"
        )

        return pd.DataFrame(
            {
                "indicator_code": 433,
                "reference_date": monthly_dates,
                "value": [0.5] * len(monthly_dates),
            }
        )

    reference_dates = pd.date_range(
        start="2016-01-01", end="2026-09-23", freq="7D"
    )

    base_value = float(indicator_code)

    return pd.DataFrame(
        {
            "indicator_code": indicator_code,
            "reference_date": reference_dates,
            "value": [
                base_value + step * 0.01
                for step in range(len(reference_dates))
            ],
        }
    )


def test_indicator_cards_show_derived_business_metrics(
    monkeypatch,
):
    at, _ = run_app(
        monkeypatch,
        history_spy=rich_history_spy,
    )

    assert at.exception == []

    caption_texts = [
        caption.value for caption in at.caption
    ]

    assert any(
        "Acumulado 12 meses" in text
        for text in caption_texts
    )
    assert any(
        "p.p. em 12 meses" in text
        for text in caption_texts
    )
    assert any(
        "em 30 dias" in text for text in caption_texts
    )


def test_period_comparison_metric_updates_with_selected_period(
    monkeypatch,
):
    at, _ = run_app(
        monkeypatch,
        history_spy=rich_history_spy,
    )

    comparison_metrics = [
        metric
        for metric in at.metric
        if metric.label.startswith(
            "Variação no período"
        )
    ]

    assert len(comparison_metrics) == 1
    assert (
        "Últimos 12 meses"
        in comparison_metrics[0].label
    )

    at.sidebar.selectbox[1].set_value(
        "Últimos 5 anos"
    ).run()

    comparison_metrics = [
        metric
        for metric in at.metric
        if metric.label.startswith(
            "Variação no período"
        )
    ]

    assert len(comparison_metrics) == 1
    assert (
        "Últimos 5 anos" in comparison_metrics[0].label
    )
