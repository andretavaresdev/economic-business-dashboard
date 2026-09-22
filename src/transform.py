from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

@dataclass(frozen=True)
class IndicatorValue:
    indicator_code: int
    reference_date: date
    value: Decimal

def transform_bcb_records(
    indicator_code: int,
    raw_records: list[dict[str, str]],
) -> list[IndicatorValue]:

    if indicator_code <= 0:
        raise ValueError("O código do indicador deve ser positivo.")

    if not raw_records:
        raise ValueError("Não existem registros para transformar.")

    transformed_records = []
    reference_dates = set()

    for position, record in enumerate(raw_records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Registro inválido na posição {position}."
            )

        raw_date = record.get("data")
        raw_value = record.get("valor")

        if not isinstance(raw_date, str):
            raise ValueError(
                f"Data inválida no registro {position}: {raw_date!r}."
            )

        if not isinstance(raw_value, str):
            raise ValueError(
                f"Valor inválido no registro {position}: {raw_value!r}."
            )

        try:
            reference_date = datetime.strptime(
                raw_date.strip(),
                "%d/%m/%Y",
            ).date()

        except ValueError as error:
            raise ValueError(
                f"Data inválida no registro {position}: {raw_date!r}."
            ) from error

        try:
            value = Decimal(
                raw_value.strip().replace(",", ".")
            )

        except InvalidOperation as error:
            raise ValueError(
                f"Valor inválido no registro {position}: {raw_value!r}."
            ) from error

        if not value.is_finite():
            raise ValueError(
                f"Valor não finito no registro {position}: {raw_value!r}."
            )

        if reference_date in reference_dates:
            raise ValueError(
                f"Data duplicada encontrada: {reference_date}."
            )

        reference_dates.add(reference_date)

        transformed_records.append(
            IndicatorValue(
                indicator_code=indicator_code,
                reference_date=reference_date,
                value=value,
            )
        )

    return sorted(
        transformed_records,
        key=lambda record: record.reference_date,
    )