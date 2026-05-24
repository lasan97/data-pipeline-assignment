from pathlib import Path

import psycopg

from src.event_generator import database_url_from_env, load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
INIT_SQL_PATH = ROOT_DIR / "db" / "init.sql"


def reset_database():
    """기존 테이블을 삭제하고 db/init.sql을 다시 실행한다."""
    load_dotenv()
    init_sql = INIT_SQL_PATH.read_text(encoding="utf-8")

    with psycopg.connect(database_url_from_env()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS events, contents, partners CASCADE")
            cursor.execute(init_sql)

    print("reset_database=ok")


def main():
    reset_database()


if __name__ == "__main__":
    main()
