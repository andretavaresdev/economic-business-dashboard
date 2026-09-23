from collections.abc import Sequence
from datetime import date

import pandas as pd

from src.database import get_connection


def execute_query(
    query: str,
    parameters: Sequence[object] = (),
) -> pd.DataFrame:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(query, parameters)

        rows = cursor.fetchall()
        description = cursor.description

    if description is None:
        return pd.DataFrame()

    columns = [
        column.name
        for column in description
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def normalize_indicator_data(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    normalized_dataframe = dataframe.copy()

    if "reference_date" in normalized_dataframe.columns:
        normalized_dataframe["reference_date"] = (
            pd.to_datetime(
                normalized_dataframe["reference_date"]
            )
        )

    if "value" in normalized_dataframe.columns:
        normalized_dataframe["value"] = (
            normalized_dataframe["value"].astype(float)
        )

    return normalized_dataframe


def get_latest_indicator_values() -> pd.DataFrame:
    query = """
        WITH latest_values AS (
            SELECT DISTINCT ON (i.codigo)
                i.codigo AS indicator_code,
                i.nome AS indicator_name,
                i.unidade AS unit,
                i.periodicidade AS frequency,
                v.data_referencia AS reference_date,
                v.valor AS value
            FROM indicadores AS i
            INNER JOIN valores_indicadores AS v
                ON v.codigo_indicador = i.codigo
            ORDER BY
                i.codigo,
                v.data_referencia DESC
        )
        SELECT
            indicator_code,
            indicator_name,
            unit,
            frequency,
            reference_date,
            value
        FROM latest_values
        ORDER BY indicator_name;
    """

    dataframe = execute_query(query)

    return normalize_indicator_data(dataframe)


def get_indicator_history(
    indicator_code: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if indicator_code <= 0:
        raise ValueError(
            "O código do indicador deve ser positivo."
        )

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise ValueError(
            "A data inicial não pode ser posterior "
            "à data final."
        )

    filters = [
        "v.codigo_indicador = %s",
    ]
    parameters: list[object] = [
        indicator_code,
    ]

    if start_date is not None:
        filters.append(
            "v.data_referencia >= %s"
        )
        parameters.append(start_date)

    if end_date is not None:
        filters.append(
            "v.data_referencia <= %s"
        )
        parameters.append(end_date)

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            i.codigo AS indicator_code,
            i.nome AS indicator_name,
            i.unidade AS unit,
            i.periodicidade AS frequency,
            v.data_referencia AS reference_date,
            v.valor AS value
        FROM valores_indicadores AS v
        INNER JOIN indicadores AS i
            ON i.codigo = v.codigo_indicador
        WHERE {where_clause}
        ORDER BY v.data_referencia;
    """

    dataframe = execute_query(
        query=query,
        parameters=parameters,
    )

    return normalize_indicator_data(dataframe)