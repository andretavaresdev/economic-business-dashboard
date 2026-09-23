from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.queries import (
    get_indicator_history,
    get_latest_indicator_values,
)


PERIOD_OPTIONS = {
    "Últimos 12 meses": 365,
    "Últimos 3 anos": 365 * 3,
    "Últimos 5 anos": 365 * 5,
}

CURRENCY_INDICATOR_CODE = 1

INDICATOR_ICONS = {
    432: "🏦",
    433: "🛒",
    1: "💵",
}

DEFAULT_INDICATOR_ICON = "📊"


def format_number_br(
    value: float,
    decimal_places: int = 2,
) -> str:
    formatted_value = (
        f"{value:,.{decimal_places}f}"
    )

    return (
        formatted_value
        .replace(",", "#")
        .replace(".", ",")
        .replace("#", ".")
    )


def is_currency_indicator(indicator_code: int) -> bool:
    return indicator_code == CURRENCY_INDICATOR_CODE


def format_indicator_value(
    indicator_code: int,
    value: float,
) -> str:
    if is_currency_indicator(indicator_code):
        return (
            f"R$ {format_number_br(value, 4)}"
        )

    return (
        f"{format_number_br(value, 2)}%"
    )


def indicator_value_axis_label(indicator_code: int) -> str:
    if is_currency_indicator(indicator_code):
        return "Valor (R$)"

    return "Valor (%)"


@st.cache_data(ttl=300)
def load_latest_values() -> pd.DataFrame:
    return get_latest_indicator_values()


@st.cache_data(ttl=300)
def load_indicator_history(
    indicator_code: int,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    return get_indicator_history(
        indicator_code=indicator_code,
        start_date=start_date,
        end_date=end_date,
    )


def render_indicator_cards(
    latest_values: pd.DataFrame,
) -> None:
    columns = st.columns(len(latest_values))

    for column, (_, indicator) in zip(
        columns,
        latest_values.iterrows(),
    ):
        indicator_code = int(
            indicator["indicator_code"]
        )
        value = float(indicator["value"])
        reference_date = indicator["reference_date"]
        icon = INDICATOR_ICONS.get(
            indicator_code, DEFAULT_INDICATOR_ICON
        )

        with column:
            with st.container(border=True):
                st.metric(
                    label=f"{icon} {indicator['indicator_name']}",
                    value=format_indicator_value(
                        indicator_code,
                        value,
                    ),
                )

                st.caption(
                    f"{indicator['frequency'].capitalize()} • "
                    f"Referência: {reference_date:%d/%m/%Y}"
                )


def render_sidebar_filters(
    latest_values: pd.DataFrame,
) -> tuple[str, str]:
    st.sidebar.header("Filtros")

    indicator_options = list(
        latest_values["indicator_name"]
    )

    selected_indicator_name = st.sidebar.selectbox(
        "Indicador",
        options=indicator_options,
    )

    selected_period = st.sidebar.selectbox(
        "Período",
        options=list(PERIOD_OPTIONS),
    )

    st.sidebar.caption(
        "Fonte: Banco Central do Brasil (SGS)."
    )

    return selected_indicator_name, selected_period


def main() -> None:
    st.set_page_config(
        page_title="Painel Econômico Brasileiro",
        page_icon="📊",
        layout="wide",
    )

    st.title("Painel Econômico Brasileiro")

    st.caption(
        "Acompanhe a Meta Selic, o IPCA e o dólar "
        "com dados do Banco Central do Brasil."
    )

    try:
        latest_values = load_latest_values()

    except Exception as error:
        st.error(
            "Não foi possível consultar o PostgreSQL. "
            "Verifique se o banco está em execução."
        )

        st.exception(error)
        st.stop()

    if latest_values.empty:
        st.warning(
            "Nenhum indicador foi encontrado. "
            "Execute o pipeline antes de abrir o dashboard."
        )
        st.stop()

    render_indicator_cards(latest_values)

    selected_indicator_name, selected_period = (
        render_sidebar_filters(latest_values)
    )

    indicator_options = {
        row["indicator_name"]: int(
            row["indicator_code"]
        )
        for _, row in latest_values.iterrows()
    }

    selected_indicator_code = (
        indicator_options[
            selected_indicator_name
        ]
    )

    selected_latest_value = latest_values.loc[
        latest_values["indicator_code"]
        == selected_indicator_code
    ].iloc[0]

    end_date = selected_latest_value[
        "reference_date"
    ].date()

    start_date = end_date - timedelta(
        days=PERIOD_OPTIONS[selected_period]
    )

    try:
        history = load_indicator_history(
            indicator_code=selected_indicator_code,
            start_date=start_date,
            end_date=end_date,
        )

    except Exception as error:
        st.error(
            "Não foi possível consultar o histórico "
            "do indicador."
        )
        st.exception(error)
        st.stop()

    st.divider()

    icon = INDICATOR_ICONS.get(
        selected_indicator_code, DEFAULT_INDICATOR_ICON
    )

    st.subheader(
        f"{icon} Histórico — {selected_indicator_name}"
    )

    if history.empty:
        st.info(
            "Não existem dados para o período selecionado."
        )
        st.stop()

    value_label = indicator_value_axis_label(
        selected_indicator_code
    )

    chart_data = history.rename(
        columns={
            "reference_date": "Data",
            "value": value_label,
        }
    )

    st.line_chart(
        chart_data,
        x="Data",
        y=value_label,
        height=400,
    )

    with st.expander("Visualizar dados"):
        table_data = chart_data[
            ["Data", value_label]
        ].copy()

        table_data["Data"] = (
            table_data["Data"].dt.strftime(
                "%d/%m/%Y"
            )
        )

        st.dataframe(
            table_data,
            hide_index=True,
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
