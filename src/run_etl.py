from datetime import date, timedelta

from src.audit import finish_etl_execution, start_etl_execution
from src.extract import extract_bcb_series
from src.load import load_indicator
from src.transform import transform_bcb_records

SELIC_CODE = 432
HISTORY_DAYS = 30

def run_pipeline(
    indicator_code: int,
    history_days: int,
) -> None:
    execution_id = start_etl_execution()

    extracted_count = 0
    loaded_count = 0

    print(f"Execução registrada com ID: {execution_id}")

    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=history_days)

        print("Iniciando pipeline da Selic.")
        print(f"Período: {start_date} até {end_date}")

        raw_records = extract_bcb_series(
            series_code=indicator_code,
            start_date=start_date,
            end_date=end_date,
        )

        extracted_count = len(raw_records)
        print(f"Registros extraídos: {extracted_count}")

        transformed_records = transform_bcb_records(
            indicator_code=indicator_code,
            raw_records=raw_records,
        )

        print(
            "Registros transformados: "
            f"{len(transformed_records)}"
        )

        loaded_count = load_indicator(
            indicator_code=indicator_code,
            name="Selic definida pelo Copom",
            unit="Percentual ao ano",
            frequency="Diária",
            source="Banco Central do Brasil",
            records=transformed_records,
        )

        print(
            "Registros processados no PostgreSQL: "
            f"{loaded_count}"
        )

    except Exception as error:
        error_message = (
            f"{type(error).__name__}: {error}"
        )

        finish_etl_execution(
            execution_id=execution_id,
            status="falha",
            extracted_records=extracted_count,
            loaded_records=loaded_count,
            error_message=error_message,
        )

        print(f"Pipeline finalizado com falha: {error_message}")

        raise
    else:
        finish_etl_execution(
            execution_id=execution_id,
            status="sucesso",
            extracted_records=extracted_count,
            loaded_records=loaded_count,
        )
        print("Pipeline finalizado com sucesso.")

def main() -> None:
    run_pipeline(
        indicator_code=SELIC_CODE,
        history_days=HISTORY_DAYS,
    )

if __name__ == "__main__":
    main()