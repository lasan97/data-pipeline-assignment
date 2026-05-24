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

FUNNEL_SCENARIOS = (
    ("landing_only", 25),
    ("content_view_only", 35),
    ("purchase_start_only", 10),
    ("purchase_complete", 25),
    ("payment_failed", 5),
)


def generate_events(sessions=100, seed=None):
    """요청한 세션 수만큼 퍼널 흐름을 따르는 이벤트 dict 목록을 생성한다.

    sessions:
        생성할 방문 세션 수.
    seed:
        같은 랜덤 결과를 재현하고 싶을 때 사용한다.
        테스트에서는 seed를 고정해서 매번 같은 이벤트가 나오게 한다.
    """
    rng = random.Random(seed)
    base_time = datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    contents = _normalize_contents(load_contents())

    events = []
    for index in range(sessions):
        events.extend(_generate_session_events(rng, base_time, index, contents))

    return events


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


def _generate_session_events(rng, base_time, index, contents):
    """세션 한 건에 해당하는 퍼널 이벤트 묶음을 생성한다."""
    scenario = _choose_scenario(rng)
    content = rng.choice(contents)
    partner_id = content["partner_id"]

    session_id = f"session_{index + 1}"
    user_id = _user_id(rng)
    device_type = rng.choice(DEVICE_TYPES)

    purchase_attempt_id = f"purchase_attempt_{index + 1}"
    payment_method = rng.choice(PAYMENT_METHODS)
    event_types = ["session_start", "landing_page_view"]

    if scenario in {
        "content_view_only",
        "purchase_start_only",
        "purchase_complete",
        "payment_failed",
    }:
        event_types.append("content_view")

    if scenario in {"purchase_start_only", "purchase_complete", "payment_failed"}:
        event_types.append("purchase_start")

    if scenario == "purchase_complete":
        event_types.append("purchase_complete")

    if scenario == "payment_failed":
        event_types.append("payment_failed")

    return [
        _build_event(
            rng=rng,
            base_time=base_time,
            session_index=index,
            step_index=step_index,
            event_type=event_type,
            partner_id=partner_id,
            user_id=user_id,
            session_id=session_id,
            device_type=device_type,
            content=content,
            purchase_attempt_id=purchase_attempt_id,
            payment_method=payment_method,
        )
        for step_index, event_type in enumerate(event_types)
    ]


def _choose_scenario(rng):
    """가중치 기반으로 세션 퍼널 시나리오를 하나 선택한다."""
    scenarios = [scenario for scenario, _weight in FUNNEL_SCENARIOS]
    weights = [weight for _scenario, weight in FUNNEL_SCENARIOS]

    return rng.choices(scenarios, weights=weights, k=1)[0]


def _build_event(
    rng,
    base_time,
    session_index,
    step_index,
    event_type,
    partner_id,
    user_id,
    session_id,
    device_type,
    content,
    purchase_attempt_id,
    payment_method,
):
    """공통 필드와 event_type별 properties를 합쳐 이벤트 한 건을 만든다."""
    return {
        "event_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "event_type": event_type,
        "occurred_at": _occurred_at(rng, base_time, session_index, step_index),
        "partner_id": partner_id,
        "user_id": user_id,
        "session_id": session_id,
        "device_type": device_type,
        "properties": _properties_for(
            event_type,
            content,
            purchase_attempt_id,
            payment_method,
            rng,
        ),
    }


def _occurred_at(rng, base_time, session_index, step_index):
    """세션은 3분 간격, 세션 안의 이벤트는 30초 간격으로 퍼져 보이게 한다."""
    #   너무 기계적으로 30초 단위만 찍히지 않도록 약간의 랜덤성을 더한다.
    offset = timedelta(
        minutes=session_index * 3,
        seconds=step_index * 30 + rng.randint(0, 20),
    )

    return (base_time + offset).isoformat()


def _user_id(rng):
    """20%는 비로그인 사용자라고 가정해 user_id를 None으로 둔다."""
    if rng.random() < 0.2:
        return None

    return f"user_{rng.randint(1, 300)}"


def _properties_for(event_type, content, purchase_attempt_id, payment_method, rng):
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
        return _purchase_properties(content, purchase_attempt_id, payment_method)

    if event_type == "purchase_complete":
        properties = _purchase_properties(content, purchase_attempt_id, payment_method)
        properties["order_id"] = f"order_{rng.randint(1, 5000)}"
        return properties

    properties = _purchase_properties(content, purchase_attempt_id, payment_method)
    error_code, error_msg = rng.choice(ERRORS)
    properties["error_code"] = error_code
    properties["error_msg"] = error_msg
    return properties


def _purchase_properties(content, purchase_attempt_id, payment_method):
    """구매 관련 이벤트에서 공통으로 쓰는 properties를 만든다."""
    price = content["price"]
    discount_amount = content["discount_amount"]
    amount = price - (discount_amount or 0)

    return {
        "content_id": content["content_id"],
        "purchase_attempt_id": purchase_attempt_id,
        "discount_amount": discount_amount,
        "amount": amount,
        "payment_method": payment_method,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed", type=int, default=None, help="재현 가능한 생성을 위한 seed")
    parser.add_argument("--sessions", type=int, default=100, help="생성할 세션 수")
    args = parser.parse_args()

    for event in generate_events(sessions=args.sessions, seed=args.seed):
        print(json.dumps(event, ensure_ascii=False))


if __name__ == "__main__":
    main()
