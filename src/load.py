from collections.abc import Sequence

from src.database import get_connection
from src.transform import IndicatorValue

def load_indicator(
    indicator_code: int,
    name: str,
    unit: str,
    frequency: str,
    source: str,
    records: Sequence[IndicatorValue],
) -> int:

    if not records:
        raise ValueError("Não existem registros para carregar.")

    invalid_records = [
        record
        for record in records
        if record.indicator_code != indicator_code
    ]

    if invalid_records:
        raise ValueError(
            "Existem registros vinculados a outro indicador."
        )

    indicator_parameters = (
        indicator_code,
        name,
        unit,
        frequency,
        source,
    )

    value_parameters = [
        (
            record.indicator_code,
            record.reference_date,
            record.value,
        )
        for record in records
    ]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO indicadores (
                    codigo,
                    nome,
                    unidade,
                    periodicidade,
                    fonte
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome,
                    unidade = EXCLUDED.unidade,
                    periodicidade = EXCLUDED.periodicidade,
                    fonte = EXCLUDED.fonte;
                """,
                indicator_parameters,
            )

            cursor.executemany(
                """
                INSERT INTO valores_indicadores (
                    codigo_indicador,
                    data_referencia,
                    valor
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (
                    codigo_indicador,
                    data_referencia
                )
                DO UPDATE SET
                    valor = EXCLUDED.valor,
                    coletado_em = CURRENT_TIMESTAMP;
                """,
                value_parameters,
            )

    return len(records)