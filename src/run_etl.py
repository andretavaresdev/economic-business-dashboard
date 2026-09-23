import argparse
from datetime import date, timedelta

from src.audit import finish_etl_execution, start_etl_execution
from src.extract import extract_bcb_series
from src.indicators import INDICATORS, Indicator, get_indicator
from src.load import get_latest_reference_date, load_indicator
from src.transform import transform_bcb_records


INITIAL_HISTORY_YEARS = 5
DEFAULT_REPROCESS_DAYS = 7

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
    reprocess_days: int = DEFAULT_REPROCESS_DAYS,
) -> date:
    if reprocess_days <= 0:
        raise ValueError(
            "A janela de reprocessamento deve ser positiva."
        )

    if backfill:
        return calculate_historical_start_date(end_date)

    latest_date = get_latest_reference_date(indicator_code)

    if latest_date is None:
        return calculate_historical_start_date(end_date)

    if latest_date > end_date:
        raise RuntimeError(
            "A última data armazenada está no futuro: "
            f"{latest_date}."
        )

    return latest_date - timedelta(
        days=reprocess_days - 1
    )


def run_pipeline(
    indicator: Indicator,
    backfill: bool = False,
) -> None:
    execution_id = start_etl_execution()

    extracted_count = 0
    loaded_count = 0

    print()
    print("=" * 60)
    print(f"Indicador: {indicator.name}")
    print(f"Código SGS: {indicator.code}")
    print(f"Execução registrada com ID: {execution_id}")

    try:
        end_date = date.today()

        start_date = determine_start_date(
            indicator_code=indicator.code,
            end_date=end_date,
            backfill=backfill,
            reprocess_days=indicator.reprocess_days,
        )

        execution_mode = (
            "histórica" if backfill else "incremental"
        )

        print(f"Modo da execução: {execution_mode}")
        print(f"Período: {start_date} até {end_date}")

        raw_records = extract_bcb_series(
            series_code=indicator.code,
            start_date=start_date,
            end_date=end_date,
        )

        extracted_count = len(raw_records)

        print(
            f"Registros extraídos: {extracted_count}"
        )

        transformed_records = transform_bcb_records(
            indicator_code=indicator.code,
            raw_records=raw_records,
        )

        print(
            "Registros transformados: "
            f"{len(transformed_records)}"
        )

        loaded_count = load_indicator(
            indicator_code=indicator.code,
            name=indicator.name,
            unit=indicator.unit,
            frequency=indicator.periodicity,
            source=indicator.source,
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

        print(
            f"Pipeline finalizado com falha: "
            f"{error_message}"
        )

        raise

    else:
        finish_etl_execution(
            execution_id=execution_id,
            status="sucesso",
            extracted_records=extracted_count,
            loaded_records=loaded_count,
        )

        print(
            f"Pipeline de {indicator.name} "
            "finalizado com sucesso."
        )


def parse_arguments() -> argparse.Namespace:
    available_indicators = [
        *INDICATORS.keys(),
        "all",
    ]

    parser = argparse.ArgumentParser(
        description=(
            "Executa o pipeline de indicadores."
        )
    )

    parser.add_argument(
        "--indicator",
        choices=available_indicators,
        default="selic",
        help=(
            "Indicador que será processado. "
            "Use 'all' para executar todos. "
            "Padrão: selic."
        ),
    )

    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Carrega novamente os últimos cinco anos.",
    )

    return parser.parse_args()

def main() -> None:
    arguments = parse_arguments()

    if arguments.indicator == "all":
        selected_indicators = INDICATORS.values()
    else:
        selected_indicators = [
            get_indicator(arguments.indicator)
        ]

    for indicator in selected_indicators:
        run_pipeline(
            indicator=indicator,
            backfill=arguments.backfill,
        )

if __name__ == "__main__":
    main()