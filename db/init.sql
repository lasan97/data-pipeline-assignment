CREATE TABLE IF NOT EXISTS partners (
    partner_id VARCHAR(50) PRIMARY KEY,
    partner_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS contents (
    content_id VARCHAR(50) PRIMARY KEY,
    partner_id VARCHAR(50) NOT NULL REFERENCES partners (partner_id),
    content_title VARCHAR(100) NOT NULL,
    price INTEGER NOT NULL,
    discount_amount INTEGER,
    CONSTRAINT contents_price_check CHECK (price >= 0),
    CONSTRAINT contents_discount_amount_check CHECK (
        discount_amount IS NULL OR (
            discount_amount >= 0 AND discount_amount <= price
        )
    )
);

CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    partner_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    session_id VARCHAR(50) NOT NULL,
    device_type VARCHAR(20),
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT events_event_type_check CHECK (
        event_type IN (
            'session_start',
            'landing_page_view',
            'content_view',
            'purchase_start',
            'purchase_complete',
            'payment_failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_partner_id ON events (partner_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events (session_id);

INSERT INTO partners (partner_id, partner_name) VALUES
    ('partner_1', '데이터 분석 강사'),
    ('partner_2', '온라인 드로잉 작가'),
    ('partner_3', '1인 창업 코치'),
    ('partner_4', '홈트레이닝 코치'),
    ('partner_5', '베이킹 클래스 운영자'),
    ('partner_6', '외국어 튜터'),
    ('partner_7', '커리어 멘토'),
    ('partner_8', '사진 보정 크리에이터'),
    ('partner_9', '재테크 강사'),
    ('partner_10', '음악 프로듀서')
ON CONFLICT (partner_id) DO NOTHING;

INSERT INTO contents (
    content_id,
    partner_id,
    content_title,
    price,
    discount_amount
) VALUES
    ('content_1', 'partner_1', 'SQL 입문 강의', 39000, NULL),
    ('content_2', 'partner_1', '파이썬 데이터 분석 실전', 59000, 10000),
    ('content_3', 'partner_1', '대시보드 기획과 지표 설계', 69000, NULL),
    ('content_4', 'partner_2', '아이패드 드로잉 기초', 45000, 5000),
    ('content_5', 'partner_2', '캐릭터 일러스트 클래스', 69000, NULL),
    ('content_6', 'partner_2', '굿즈 제작을 위한 디지털 그림', 52000, 7000),
    ('content_7', 'partner_2', '웹툰 콘티와 연출 입문', 74000, NULL),
    ('content_8', 'partner_3', '1인 창업 시작하기', 49000, 7000),
    ('content_9', 'partner_3', '전자책 판매 전략', 55000, NULL),
    ('content_10', 'partner_4', '하루 20분 홈트 루틴', 33000, NULL),
    ('content_11', 'partner_4', '초보자를 위한 근력 운동', 43000, 5000),
    ('content_12', 'partner_4', '식단 기록과 체형 관리', 39000, NULL),
    ('content_13', 'partner_5', '처음 배우는 홈베이킹', 46000, NULL),
    ('content_14', 'partner_5', '마카롱 실패 줄이기', 62000, 8000),
    ('content_15', 'partner_5', '구움과자 판매 준비반', 79000, NULL),
    ('content_16', 'partner_5', '카페 디저트 레시피', 69000, 10000),
    ('content_17', 'partner_5', '베이킹 원가 계산 실습', 35000, NULL),
    ('content_18', 'partner_6', '비즈니스 영어 이메일', 41000, NULL),
    ('content_19', 'partner_6', '여행 영어 회화 패턴', 37000, 4000),
    ('content_20', 'partner_6', '일본어 초급 문법 정리', 39000, NULL),
    ('content_21', 'partner_7', '이직 포트폴리오 만들기', 54000, 7000),
    ('content_22', 'partner_7', '면접 답변 구조화 워크숍', 49000, NULL),
    ('content_23', 'partner_7', '주니어 개발자 커리어 로드맵', 65000, 10000),
    ('content_24', 'partner_7', '링크드인 프로필 개선하기', 32000, NULL),
    ('content_25', 'partner_8', '라이트룸 색감 보정 기초', 45000, 5000),
    ('content_26', 'partner_8', '인물 사진 보정 실전', 58000, NULL),
    ('content_27', 'partner_9', '월급 관리와 예산 세우기', 39000, NULL),
    ('content_28', 'partner_9', '초보자를 위한 ETF 투자', 62000, 8000),
    ('content_29', 'partner_9', '부동산 투자 용어 정리', 44000, NULL),
    ('content_30', 'partner_10', '로직 프로 작곡 입문', 57000, NULL),
    ('content_31', 'partner_10', '홈레코딩 장비 세팅', 48000, 6000),
    ('content_32', 'partner_10', '보컬 믹싱 기본기', 72000, NULL),
    ('content_33', 'partner_10', '비트메이킹 실전 패턴', 66000, 9000),
    ('content_34', 'partner_10', '음원 발매 준비 체크리스트', 36000, NULL)
ON CONFLICT (content_id) DO NOTHING;
