import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import psycopg
from dotenv import dotenv_values

EVENT_TYPES = (
    "session_start",
    "landing_page_view",
    "content_view",
    "purchase_start",
    "purchase_complete",
    "payment_failed",
)

DEVICE_TYPES = ("desktop", "mobile", "tablet")
LANDING_PAGES = ("/", "/courses", "/creators", "/event/spring-sale")
REFERRERS = (None, "https://google.com", "https://naver.com", "https://instagram.com")
UTM_SOURCES = (None, "google", "naver", "instagram", "newsletter")
UTM_CAMPAIGNS = (None, "spring_sale", "new_creator", "retargeting")
PAYMENT_METHODS = ("card", "kakao_pay", "naver_pay", "bank_transfer")
ERRORS = (
    ("CARD_DECLINED", "카드 승인이 거절되었습니다."),
    ("TIMEOUT", "결제 요청 시간이 초과되었습니다."),
    ("INVALID_AUTH", "결제 인증에 실패했습니다."),
)


def generate_events(count=100, seed=None):
    """요청한 개수만큼 랜덤 이벤트 dict 목록을 생성한다.

    count:
        생성할 이벤트 개수.
    seed:
        같은 랜덤 결과를 재현하고 싶을 때 사용한다.
        테스트에서는 seed를 고정해서 매번 같은 이벤트가 나오게 한다.
    """
    rng = random.Random(seed)
    base_time = datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    contents = _normalize_contents(load_contents())
    partner_ids = tuple(sorted({content["partner_id"] for content in contents}))

    return [
        _generate_event(rng, base_time, index, contents, partner_ids)
        for index in range(count)
    ]


def load_contents():
    """Postgres contents 테이블에서 이벤트 생성에 필요한 seed 데이터를 읽는다."""
    load_dotenv()

    query = """
        SELECT content_id, partner_id, price, discount_amount
        FROM contents
        ORDER BY content_id
    """

    with psycopg.connect(database_url_from_env()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return [
        {
            "content_id": row[0],
            "partner_id": row[1],
            "price": row[2],
            "discount_amount": row[3],
        }
        for row in rows
    ]


def database_url_from_env():
    """환경변수 값을 Postgres 접속 URL 문자열로 조합한다."""

    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "liveklass")
    user = os.environ.get("DB_USER", "liveklass")
    password = os.environ.get("DB_PASSWORD")

    if not password:
        raise RuntimeError("DB_PASSWORD 환경변수가 필요합니다.")

    return (
        f"postgresql://{quote(user)}:{quote(password)}"
        f"@{host}:{port}/{quote(name)}"
    )


def load_dotenv():
    """.env 파일을 읽어 os.environ에 채운다."""

    for key, value in dotenv_values(".env").items():
        if value is not None and key not in os.environ:
            os.environ[key] = value


def _normalize_contents(contents):
    """콘텐츠 seed 데이터가 비어 있지 않은지 확인한다."""

    normalized = tuple(dict(content) for content in contents)

    if not normalized:
        raise ValueError("이벤트 생성을 위해 contents seed 데이터가 필요합니다.")
    return normalized


def _generate_event(rng, base_time, index, contents, partner_ids):
    """이벤트 한 건을 생성한다."""

    event_type = rng.choice(EVENT_TYPES)
    content = rng.choice(contents)

    partner_id = content["partner_id"] if _uses_content(event_type) else rng.choice(partner_ids)
    purchase_attempt_id = f"purchase_attempt_{rng.randint(1, 5000)}"

    return {
        "event_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "event_type": event_type,
        "occurred_at": _occurred_at(rng, base_time, index),
        "partner_id": partner_id,
        "user_id": _user_id(rng),
        "session_id": f"session_{rng.randint(1, 2000)}",
        "device_type": rng.choice(DEVICE_TYPES),
        "properties": _properties_for(event_type, content, purchase_attempt_id, rng),
    }


def _uses_content(event_type):
    """이벤트 타입이 특정 콘텐츠와 연결되는지 판단한다."""
    return event_type in {
        "content_view",
        "purchase_start",
        "purchase_complete",
        "payment_failed",
    }


def _occurred_at(rng, base_time, index):
    """index * 3분을 더해 이벤트가 시간 순서대로 퍼져 보이게 한다."""
    offset = timedelta(minutes=index * 3 + rng.randint(0, 2), seconds=rng.randint(0, 59))
    return (base_time + offset).isoformat()


def _user_id(rng):
    """20%는 비로그인 사용자라고 가정해 user_id를 None으로 둔다."""
    if rng.random() < 0.2:
        return None

    return f"user_{rng.randint(1, 300)}"


def _properties_for(event_type, content, purchase_attempt_id, rng):
    """event_type별 properties 값을 만든다."""
    if event_type == "session_start":
        return {}

    if event_type == "landing_page_view":
        return {
            "landing_page": rng.choice(LANDING_PAGES),
            "referrer": rng.choice(REFERRERS),
            "utm_source": rng.choice(UTM_SOURCES),
            "utm_campaign": rng.choice(UTM_CAMPAIGNS),
        }

    if event_type == "content_view":
        return {"content_id": content["content_id"]}

    if event_type == "purchase_start":
        return _purchase_properties(content, purchase_attempt_id, rng)

    if event_type == "purchase_complete":
        properties = _purchase_properties(content, purchase_attempt_id, rng)
        properties["order_id"] = f"order_{rng.randint(1, 5000)}"
        return properties

    properties = _purchase_properties(content, purchase_attempt_id, rng)
    error_code, error_msg = rng.choice(ERRORS)
    properties["error_code"] = error_code
    properties["error_msg"] = error_msg
    return properties


def _purchase_properties(content, purchase_attempt_id, rng):
    """구매 관련 이벤트에서 공통으로 쓰는 properties를 만든다."""
    price = content["price"]
    discount_amount = content["discount_amount"]
    amount = price - (discount_amount or 0)

    return {
        "content_id": content["content_id"],
        "purchase_attempt_id": purchase_attempt_id,
        "discount_amount": discount_amount,
        "amount": amount,
        "payment_method": rng.choice(PAYMENT_METHODS),
    }


def main():
    parser = argparse.ArgumentParser()

    # --seed 1처럼 seed를 주면 같은 랜덤 이벤트를 다시 만들 수 있다.
    parser.add_argument("--seed", type=int, default=None, help="재현 가능한 생성을 위한 seed")
    parser.add_argument("--count", type=int, default=100, help="생성할 이벤트 수")
    args = parser.parse_args()

    for event in generate_events(count=args.count, seed=args.seed):
        print(json.dumps(event, ensure_ascii=False))


if __name__ == "__main__":
    main()
