from datetime import date
from decimal import Decimal

import pytest

from src.transform import IndicatorValue, transform_bcb_records


def test_transforms_and_sorts_valid_records() -> None:
    raw_records = [
        {"data": "24/08/2026", "valor": "14.00"},
        {"data": "23/08/2026", "valor": "13,75"},
    ]

    result = transform_bcb_records(
        indicator_code=432,
        raw_records=raw_records,
    )

    assert result == [
        IndicatorValue(
            indicator_code=432,
            reference_date=date(2026, 8, 23),
            value=Decimal("13.75"),
        ),
        IndicatorValue(
            indicator_code=432,
            reference_date=date(2026, 8, 24),
            value=Decimal("14.00"),
        ),
    ]


def test_rejects_empty_record_list() -> None:
    with pytest.raises(
        ValueError,
        match="Não existem registros",
    ):
        transform_bcb_records(
            indicator_code=432,
            raw_records=[],
        )


def test_rejects_invalid_indicator_code() -> None:
    with pytest.raises(
        ValueError,
        match="deve ser positivo",
    ):
        transform_bcb_records(
            indicator_code=0,
            raw_records=[
                {"data": "23/08/2026", "valor": "14.00"}
            ],
        )


def test_rejects_invalid_date() -> None:
    with pytest.raises(
        ValueError,
        match="Data inválida",
    ):
        transform_bcb_records(
            indicator_code=432,
            raw_records=[
                {"data": "2026-08-23", "valor": "14.00"}
            ],
        )


def test_rejects_invalid_value() -> None:
    with pytest.raises(
        ValueError,
        match="Valor inválido",
    ):
        transform_bcb_records(
            indicator_code=432,
            raw_records=[
                {"data": "23/08/2026", "valor": "abc"}
            ],
        )


def test_rejects_non_finite_value() -> None:
    with pytest.raises(
        ValueError,
        match="Valor não finito",
    ):
        transform_bcb_records(
            indicator_code=432,
            raw_records=[
                {"data": "23/08/2026", "valor": "NaN"}
            ],
        )


def test_rejects_duplicate_dates() -> None:
    with pytest.raises(
        ValueError,
        match="Data duplicada",
    ):
        transform_bcb_records(
            indicator_code=432,
            raw_records=[
                {"data": "23/08/2026", "valor": "14.00"},
                {"data": "23/08/2026", "valor": "14.25"},
            ],
        )