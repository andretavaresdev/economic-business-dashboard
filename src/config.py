import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

def get_database_config() -> dict:
    environment_variables = {
        "dbname": "POSTGRES_DB",
        "user": "POSTGRES_USER",
        "password": "POSTGRES_PASSWORD",
        "host": "POSTGRES_HOST",
        "port": "POSTGRES_PORT",
    }

    missing_variables = [
        variable
        for variable in environment_variables.values()
        if not os.getenv(variable)
    ]

    if missing_variables:
        variables = ", ".join(missing_variables)
        raise RuntimeError(
            f"Variáveis de ambiente não configuradas: {variables}"
        )

    return {
        parameter: os.environ[variable]
        for parameter, variable in environment_variables.items()
    }