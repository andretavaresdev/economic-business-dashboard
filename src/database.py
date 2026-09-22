import psycopg
from src.config import get_database_config

def get_connection():
    database_config = get_database_config()
    return psycopg.connect(**database_config)

def check_database_connection() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version();
                """
            )
            database_name, database_user, postgres_version = cursor.fetchone()

    print("Conexão com o PostgreSQL realizada com sucesso.")
    print(f"Banco: {database_name}")
    print(f"Usuário: {database_user}")
    print(f"Versão: {postgres_version}")

if __name__ == "__main__":
    check_database_connection()