# 이벤트 로그 파이프라인 구축 및 분석
## 시나리오
이 프로젝트는 파트너(개인 강사나 창작자)가 콘텐츠를 판매하는 사이트를 운영하며, 운영 데이터를 기반으로 판매 개선 컨설팅을 제공하는 플랫폼을 가정한다.

## 기술 스택
- python
  - 이벤트 생성, 데이터 적재, 집계 분석, 시각화를 하나의 언어로 처리하기 쉽다.
  - 데이터 분석과 시각화 생태계를 활용할 수 있다.
- postgres
  - 이벤트 타입, 파트너, 시간대 기준 집계를 SQL로 작성하기 쉽다.
  - 이 프로젝트는 파트너, 이벤트 타입, 시간대처럼 명확한 기준으로 집계하는 것이 중요하므로 NoSQL보다 Postgres가 더 적합하다고 판단함.

## 요구사항 
- 이벤트 로그를 통해서 각 파트너 고객의 유입, 콘텐츠 관심도, 구매 전환, 에러를 분석해 개선 컨설팅에 활용할 수 있어야한다.
- 이벤트별 상세 속성은 properties에 저장해 이벤트 타입별로 다른 정보를 유연하게 기록할 수 있어야 한다.

## 이벤트 종류
[이벤트 디자인](./docs/EventDesign.md)
- `방문 시작` - session_start
- `유입 페이지 조회` - landing_page_view
- `콘텐츠 상세 조회` - content_view
- `구매 시작` - purchase_start
- `구매 완료` - purchase_complete
- `구매 실패` - payment_failed

## 목표
이 프로젝트로 얻고자하는 가상의 인사이트

| 분석 질문 | 필요한 이벤트 | 주요 필드 | 컨설팅 액션                                                                  |
|---|---|---|-------------------------------------------------------------------------|
| 방문자는 충분히 들어오는가? | session_start | timestamp, partner_id, session_id, device_type | 파트너별 방문 수와 방문 추이를 확인해 유입 확대가 필요한 파트너를 찾는다.                              |
| 유입 채널별 방문 비중을 확인할 수 있는가? | landing_page_view | partner_id, session_id, landing_page, referrer, utm_source, utm_campaign | 성과가 좋은 유입 채널과 캠페인을 확인해 광고 예산과 콘텐츠 홍보 채널을 조정한다.                          |
| 방문자가 콘텐츠 상세 페이지까지 이동하는가? | session_start, content_view | partner_id, session_id, content_id | 방문자의 콘텐츠 조회로 이어지는 비율을 확인해 홈, 유입 페이지, 콘텐츠 목록 등에서 콘텐츠 노출 방식과 CTA를 개선한다. |
| 콘텐츠 상세 조회가 구매로 이어지는가? | content_view, purchase_start, purchase_complete | partner_id, session_id, user_id, content_id, purchase_attempt_id, amount | 조회 대비 구매 시작률과 구매 완료율이 낮은 콘텐츠를 찾아 가격, 설명, 혜택 구성을 개선한다.                   |
| 결제에서 실패하는가? | purchase_start, purchase_complete, payment_failed | partner_id, session_id, purchase_attempt_id, payment_method, error_code, error_msg | 결제 실패율이 높은 결제 수단, 디바이스, 오류 코드를 찾아 결제 UX와 오류 대응을 개선한다.                   |

## 실행 전 준비
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m src.reset_db
```

이벤트 생성기는 `contents` 시드 데이터를 기반으로 세션 단위 랜덤 이벤트를 만든다.

```text
session_start
→ landing_page_view
  → 이탈
  → content_view
    → 이탈
    → purchase_start
      → 이탈
      → purchase_complete
      → payment_failed
```

## 이벤트 생성
```bash
python3 -m src.event_generator --sessions 100 --seed 1
```

## 이벤트 저장
`--seed`를 지정하면 같은 이벤트를 다시 생성할 수 있다.
```bash
python3 -m src.event_store --sessions 100 --seed 1
```

## 결과 시각화
```bash
python3 -m src.dashboard --host 127.0.0.1 --port 8050
```

브라우저에서 `http://127.0.0.1:8050`으로 접속한다.