import argparse

import psycopg
from psycopg.types.json import Jsonb

from src.event_generator import database_url_from_env, generate_events, load_dotenv


def insert_events(events):
    """이벤트 목록을 Postgres events 테이블에 저장한다."""
    load_dotenv()

    query = """
        INSERT INTO events (
            event_id,
            event_type,
            occurred_at,
            partner_id,
            user_id,
            session_id,
            device_type,
            properties
        ) VALUES (
            %(event_id)s,
            %(event_type)s,
            %(occurred_at)s,
            %(partner_id)s,
            %(user_id)s,
            %(session_id)s,
            %(device_type)s,
            %(properties)s
        )
        ON CONFLICT (event_id) DO NOTHING
    """

    rows = [
        {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "occurred_at": event["occurred_at"],
            "partner_id": event["partner_id"],
            "user_id": event["user_id"],
            "session_id": event["session_id"],
            "device_type": event["device_type"],
            "properties": Jsonb(event["properties"]),
        }
        for event in events
    ]

    with psycopg.connect(database_url_from_env()) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)
            inserted_count = cursor.rowcount

    return inserted_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None, help="재현 가능한 생성을 위한 seed")
    parser.add_argument("--count", type=int, default=100, help="생성 후 저장할 이벤트 수")
    args = parser.parse_args()

    events = generate_events(count=args.count, seed=args.seed)
    inserted_count = insert_events(events)
    print(f"inserted_events={inserted_count}")


if __name__ == "__main__":
    main()
