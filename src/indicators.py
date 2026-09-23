from dataclasses import dataclass


@dataclass(frozen=True)
class Indicator:
    code: int
    name: str
    unit: str
    periodicity: str
    source: str
    reprocess_days: int

INDICATORS = {
    "selic": Indicator(
        code=432,
        name="Selic",
        unit="% ao ano",
        periodicity="diária",
        source="Banco Central do Brasil",
        reprocess_days=7,
    ),
    "ipca": Indicator(
        code=433,
        name="IPCA",
        unit="% ao mês",
        periodicity="mensal",
        source="Banco Central do Brasil",
        reprocess_days=90,
    ),
    "dolar": Indicator(
        code=1,
        name="Dólar comercial",
        unit="R$/US$",
        periodicity="diária",
        source="Banco Central do Brasil",
        reprocess_days=7,
    ),
}


def get_indicator(indicator_name: str) -> Indicator:
    normalized_name = indicator_name.strip().lower()

    try:
        return INDICATORS[normalized_name]
    except KeyError as error:
        available_indicators = ", ".join(INDICATORS)

        raise ValueError(
            f"Indicador '{indicator_name}' não encontrado. "
            f"Opções disponíveis: {available_indicators}."
        ) from error