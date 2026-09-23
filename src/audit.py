from src.database import get_connection


FINAL_STATUSES = {"sucesso", "falha"}


def start_etl_execution(
    indicator_code: int,
) -> int:
    if indicator_code <= 0:
        raise ValueError(
            "O código do indicador deve ser positivo."
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO execucoes_etl (
                    codigo_indicador,
                    status
                )
                VALUES (
                    %s,
                    'em_execucao'
                )
                RETURNING id;
                """,
                (indicator_code,),
            )

            result = cursor.fetchone()

    if result is None:
        raise RuntimeError(
            "Não foi possível registrar o início da execução."
        )

    return result[0]

def finish_etl_execution(
    execution_id: int,
    status: str,
    extracted_records: int,
    loaded_records: int,
    error_message: str | None = None,
) -> None:
    if status not in FINAL_STATUSES:
        raise ValueError(
            f"Status final inválido: {status!r}."
        )

    if extracted_records < 0 or loaded_records < 0:
        raise ValueError(
            "As quantidades de registros não podem ser negativas."
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE execucoes_etl
                SET
                    finalizado_em = CURRENT_TIMESTAMP,
                    status = %s,
                    registros_extraidos = %s,
                    registros_carregados = %s,
                    mensagem_erro = %s
                WHERE id = %s;
                """,
                (
                    status,
                    extracted_records,
                    loaded_records,
                    error_message,
                    execution_id,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    f"Execução {execution_id} não encontrada."
                )