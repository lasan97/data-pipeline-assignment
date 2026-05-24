# 이벤트

## 공통 필드
- event_id - `이벤트 아이디`
- event_type - `이벤트 종류`
- timestamp - `이벤트 발생 시간`
- partner_id - `파트너 ID`
- user_id - `사용자 ID, 비로그인은 null`, nullable
- session_id - `세션 ID`
- device_type - `디바이스 종류`, nullable

## 이벤트 설계
- `방문 시작`
  - event_name:
    - session_start
  - why:
    - 얼마나 방문하는지? 
    - 파트너별 방문 수와 방문 추이를 확인하기 위해 수집한다.
    - 유입부터 구매까지의 퍼널 분석에서 세션의 시작점으로 사용한다.
  - properties:
    - 없음
  - used_for_analysis:
    - 파트너별 방문 수 추이

- `유입 페이지 조회`
  - event_name: 
    - landing_page_view
  - why:
    - 어디서 오는지?
    - 사용자가 어떤 채널과 랜딩 페이지를 통해 파트너 사이트에 유입되었는지 확인하기 위해 수집한다.
    - 유입 채널별 방문 비중과 이후 구매 전환율을 분석하기 위해 필요하다.
  - properties:
    - landing_page (처음 도착한 페이지)
    - referrer (이전 외부 페이지, nullable) 
    - utm_source (유입 출처 - 링크, ex: naver, google, nullable)
    - utm_campaign (캠페인 이름 - 링크, nullable)
  - used_for_analysis:
    - 유입 채널별 방문 수
    - 유입 채널별 방문 비중
    - 랜딩 페이지별 방문 수
    - 유입 채널별 구매 전환율

- `콘텐츠 상세 조회`
  - event_name: 
    - content_view
  - why:
    - 얼마나 보는지?
    - 방문자가 특정 콘텐츠에 관심을 보였는지 확인하기 위해 수집한다.
    - 단순 방문 수만으로는 어떤 콘텐츠에 관심이 있는지 알 수 없기 때문에 콘텐츠 단위 조회 이벤트가 필요하다.
  - properties:
    - content_id (콘텐츠 ID)
  - used_for_analysis:
    - 콘텐츠별 상세 조회 수
    - 콘텐츠 상세 조회 대비 구매 전환율

- `구매 시작`
  - event_name: 
    - purchase_start
  - why:
    - 상세 조회에서 결제 시작까지의 전환율을 분석하는데 사용한다.
  - properties:
    - content_id (콘텐츠 ID)
    - purchase_attempt_id (구매 시도 ID)
    - price (가격)
    - discount_amount (할인금액, nullable)
  - used_for_analysis:
    - 콘텐츠 상세 조회 대비 결제 시작률
    - 콘텐츠별 결제 시작 수
    - 파트너별 구매 시도 사용자 수

- `구매 완료`
  - event_name: 
    - purchase_complete
  - why:
    - 실제로 콘텐츠를 구매 했는지?
    - 콘텐츠별 구매 전환율 분석에 사용한다.
  - properties:
    - content_id (콘텐츠 ID)
    - purchase_attempt_id (구매 시도 ID)
    - order_id (주문 ID)
    - amount (주문금액)
    - payment_method (결제 방법)
  - used_for_analysis:
    - 구매 전환율 계산
    - 파트너별 매출
    - 콘텐츠별 매출

- `구매 실패`
  - event_name: 
    - payment_failed
  - why:
    - 결제 과정에서 발생하는 실패를 확인해 매출 손실 원인을 분석하기 위해 수집한다.
    - 특정 결제 수단, 파트너, 디바이스에서 실패가 집중되는지 확인할 수 있다.
  - properties:
    - content_id (콘텐츠 ID)
    - purchase_attempt_id (구매 시도 ID)
    - amount (주문금액)
    - payment_method (결제 방법)
    - error_code (에러코드)
    - error_msg (에러메시지)
  - used_for_analysis:
    - 결제 실패 수, 실패율
    - 결제 수단 실패율

