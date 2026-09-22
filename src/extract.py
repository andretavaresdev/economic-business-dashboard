from datetime import date, timedelta

import requests


BCB_API_URL = (
    "https://api.bcb.gov.br/dados/serie/"
    "bcdata.sgs.{series_code}/dados"
)

REQUEST_TIMEOUT = 30


def extract_bcb_series(
    series_code: int,
    start_date: date,
    end_date: date,
) -> list[dict[str, str]]:

    if start_date > end_date:
        raise ValueError(
            "A data inicial não pode ser posterior à data final."
        )

    url = BCB_API_URL.format(series_code=series_code)

    parameters = {
        "formato": "json",
        "dataInicial": start_date.strftime("%d/%m/%Y"),
        "dataFinal": end_date.strftime("%d/%m/%Y"),
    }

    try:
        response = requests.get(
            url,
            params=parameters,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        records = response.json()

    except requests.exceptions.JSONDecodeError as error:
        raise RuntimeError(
            "A API do Banco Central retornou uma resposta inválida."
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            f"Falha ao consultar a série {series_code}."
        ) from error

    if not isinstance(records, list):
        raise RuntimeError(
            f"Formato inesperado para a série {series_code}."
        )

    if not records:
        raise RuntimeError(
            f"Nenhum registro encontrado para a série {series_code}."
        )

    required_fields = {"data", "valor"}

    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise RuntimeError(
                f"Registro inválido na posição {position}."
            )

        missing_fields = required_fields - record.keys()

        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise RuntimeError(
                f"Registro {position} sem os campos: {fields}."
            )

    return records


def main() -> None:
    series_code = 432
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    records = extract_bcb_series(
        series_code=series_code,
        start_date=start_date,
        end_date=end_date,
    )

    print(f"Série consultada: {series_code}")
    print(f"Período: {start_date} até {end_date}")
    print(f"Registros extraídos: {len(records)}")
    print("\nPrimeiros registros:")

    for record in records[:5]:
        print(record)


if __name__ == "__main__":
    main()