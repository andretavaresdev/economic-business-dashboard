from datetime import date, timedelta

from src.extract import extract_bcb_series
from src.load import load_indicator
from src.transform import transform_bcb_records

SELIC_CODE = 432
HISTORY_DAYS = 30

def main() -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=HISTORY_DAYS)

    print("Iniciando pipeline da Selic.")
    print(f"Período: {start_date} até {end_date}")

    raw_records = extract_bcb_series(
        series_code=SELIC_CODE,
        start_date=start_date,
        end_date=end_date,
    )

    print(f"Registros extraídos: {len(raw_records)}")

    transformed_records = transform_bcb_records(
        indicator_code=SELIC_CODE,
        raw_records=raw_records,
    )

    print(f"Registros transformados: {len(transformed_records)}")

    loaded_records = load_indicator(
        indicator_code=SELIC_CODE,
        name="Selic definida pelo Copom",
        unit="Percentual ao ano",
        frequency="Diária",
        source="Banco Central do Brasil",
        records=transformed_records,
    )

    print(f"Registros processados no PostgreSQL: {loaded_records}")
    print("Pipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()