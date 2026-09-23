import argparse
from datetime import date, timedelta

from src.audit import finish_etl_execution, start_etl_execution
from src.extract import extract_bcb_series
from src.load import get_latest_reference_date, load_indicator
from src.transform import transform_bcb_records

SELIC_CODE = 432
INITIAL_HISTORY_YEARS = 5
REPROCESS_DAYS = 7

def calculate_historical_start_date(
    end_date: date,
) -> date:
    target_year = end_date.year - INITIAL_HISTORY_YEARS

    try:
        return end_date.replace(year=target_year)

    except ValueError:
        return end_date.replace(
            year=target_year,
            month=2,
            day=28,
        )


def determine_start_date(
    indicator_code: int,
    end_date: date,
    backfill: bool,
) -> date:

    latest_date = get_latest_reference_date(indicator_code)

    if backfill or latest_date is None:
        return calculate_historical_start_date(end_date)

    if latest_date > end_date:
        raise RuntimeError(
            "A última data armazenada está no futuro: "
            f"{latest_date}."
        )

    return latest_date - timedelta(
        days=REPROCESS_DAYS - 1
    )


def run_pipeline(
    indicator_code: int,
    backfill: bool = False,
) -> None:
    execution_id = start_etl_execution()

    extracted_count = 0
    loaded_count = 0

    print(f"Execução registrada com ID: {execution_id}")

    try:
        end_date = date.today()

        start_date = determine_start_date(
            indicator_code=indicator_code,
            end_date=end_date,
            backfill=backfill,
        )

        execution_mode = (
            "histórica" if backfill else "incremental"
        )

        print(f"Modo da execução: {execution_mode}")
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

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o pipeline da Meta Selic."
    )

    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Carrega os últimos cinco anos.",
    )

    return parser.parse_args()

def main() -> None:
    arguments = parse_arguments()

    run_pipeline(
        indicator_code=SELIC_CODE,
        backfill=arguments.backfill,
    )

if __name__ == "__main__":
    main()