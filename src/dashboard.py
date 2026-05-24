import argparse

import plotly.graph_objects as go
import psycopg
from dash import Dash, dcc, html

from src.event_generator import database_url_from_env, load_dotenv


def fetch_rows(query):
    load_dotenv()
    with psycopg.connect(database_url_from_env()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def fetch_kpis():
    rows = fetch_rows(
        """
        SELECT
            COUNT(*) FILTER (WHERE event_type = 'session_start') AS visits,
            COUNT(*) FILTER (WHERE event_type = 'content_view') AS content_views,
            COUNT(*) FILTER (WHERE event_type = 'purchase_start') AS purchase_starts,
            COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
            COUNT(*) FILTER (WHERE event_type = 'payment_failed') AS payment_failures,
            COALESCE(SUM((properties->>'amount')::integer) FILTER (
                WHERE event_type = 'purchase_complete'
            ), 0) AS revenue
        FROM events
        """
    )
    row = rows[0]
    visits = row[0] or 0
    content_views = row[1] or 0
    purchase_starts = row[2] or 0
    purchases = row[3] or 0
    payment_failures = row[4] or 0
    revenue = row[5] or 0

    return {
        "visits": visits,
        "content_views": content_views,
        "purchase_starts": purchase_starts,
        "purchases": purchases,
        "payment_failures": payment_failures,
        "revenue": revenue,
        "content_view_rate": _rate(content_views, visits),
        "purchase_rate": _rate(purchases, content_views),
        "payment_failure_rate": _rate(payment_failures, purchases + payment_failures),
    }


def _rate(numerator, denominator):
    if not denominator:
        return 0
    return round(numerator / denominator * 100, 1)


def partner_visit_figure():
    rows = fetch_rows(
        """
        SELECT
            partner_id,
            COUNT(*) AS visit_count
        FROM events
        WHERE event_type = 'session_start'
        GROUP BY partner_id
        ORDER BY visit_count DESC
        """
    )
    return go.Figure(
        data=[
            go.Bar(
                x=[row[0] for row in rows],
                y=[row[1] for row in rows],
                marker_color="#4C78A8",
            )
        ],
        layout=_layout(
            "방문자는 충분히 들어오는가?",
            "파트너별 방문 시작 수",
            xaxis_title="Partner",
            yaxis_title="Visits",
        ),
    )


def utm_source_figure():
    rows = fetch_rows(
        """
        SELECT
            COALESCE(properties->>'utm_source', 'none') AS utm_source,
            COUNT(*) AS visit_count
        FROM events
        WHERE event_type = 'landing_page_view'
        GROUP BY utm_source
        ORDER BY visit_count DESC
        """
    )
    return go.Figure(
        data=[
            go.Pie(
                labels=[row[0] for row in rows],
                values=[row[1] for row in rows],
                hole=0.45,
            )
        ],
        layout=_layout(
            "유입 채널별 방문 비중",
            "landing_page_view의 utm_source 기준",
        ),
    )


def partner_funnel_figure():
    rows = fetch_rows(
        """
        SELECT
            partner_id,
            COUNT(*) FILTER (WHERE event_type = 'session_start') AS visits,
            COUNT(*) FILTER (WHERE event_type = 'content_view') AS content_views,
            COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases
        FROM events
        GROUP BY partner_id
        ORDER BY partner_id
        """
    )
    partners = [row[0] for row in rows]
    return go.Figure(
        data=[
            go.Bar(name="방문 시작", x=partners, y=[row[1] for row in rows]),
            go.Bar(name="콘텐츠 상세 조회", x=partners, y=[row[2] for row in rows]),
            go.Bar(name="구매 완료", x=partners, y=[row[3] for row in rows]),
        ],
        layout=_layout(
            "방문자가 콘텐츠 상세 페이지까지 이동하는가?",
            "파트너별 방문 → 상세 조회 → 구매 완료",
            xaxis_title="Partner",
            yaxis_title="Event Count",
            barmode="group",
        ),
    )


def content_conversion_figure():
    rows = fetch_rows(
        """
        WITH content_views AS (
            SELECT
                properties->>'content_id' AS content_id,
                COUNT(*) AS view_count
            FROM events
            WHERE event_type = 'content_view'
            GROUP BY properties->>'content_id'
        ),
        purchases AS (
            SELECT
                properties->>'content_id' AS content_id,
                COUNT(*) AS purchase_count
            FROM events
            WHERE event_type = 'purchase_complete'
            GROUP BY properties->>'content_id'
        )
        SELECT
            contents.content_title,
            COALESCE(content_views.view_count, 0) AS view_count,
            COALESCE(purchases.purchase_count, 0) AS purchase_count,
            ROUND(
                COALESCE(purchases.purchase_count, 0)::numeric
                / NULLIF(COALESCE(content_views.view_count, 0), 0)
                * 100,
                1
            ) AS conversion_rate
        FROM contents
        LEFT JOIN content_views ON content_views.content_id = contents.content_id
        LEFT JOIN purchases ON purchases.content_id = contents.content_id
        WHERE COALESCE(content_views.view_count, 0) > 0
        ORDER BY conversion_rate DESC NULLS LAST, view_count DESC
        LIMIT 10
        """
    )
    return go.Figure(
        data=[
            go.Bar(
                x=[float(row[3] or 0) for row in rows],
                y=[row[0] for row in rows],
                orientation="h",
                marker_color="#54A24B",
                customdata=[[row[1], row[2]] for row in rows],
                hovertemplate=(
                    "조회 수=%{customdata[0]}<br>"
                    "구매 수=%{customdata[1]}<br>"
                    "전환율=%{x}%<extra></extra>"
                ),
            )
        ],
        layout=_layout(
            "콘텐츠 상세 조회가 구매로 이어지는가?",
            "콘텐츠별 조회 대비 구매 완료율 Top 10",
            xaxis_title="Purchase Conversion (%)",
            yaxis_title="Content",
        ),
    )


def payment_failure_figure():
    rows = fetch_rows(
        """
        SELECT
            properties->>'payment_method' AS payment_method,
            COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
            COUNT(*) FILTER (WHERE event_type = 'payment_failed') AS failures,
            ROUND(
                COUNT(*) FILTER (WHERE event_type = 'payment_failed')::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                1
            ) AS failure_rate
        FROM events
        WHERE event_type IN ('purchase_complete', 'payment_failed')
        GROUP BY payment_method
        ORDER BY failure_rate DESC
        """
    )
    return go.Figure(
        data=[
            go.Bar(
                x=[row[0] for row in rows],
                y=[float(row[3] or 0) for row in rows],
                marker_color="#E45756",
                customdata=[[row[1], row[2]] for row in rows],
                hovertemplate=(
                    "구매 완료=%{customdata[0]}<br>"
                    "결제 실패=%{customdata[1]}<br>"
                    "실패율=%{y}%<extra></extra>"
                ),
            )
        ],
        layout=_layout(
            "결제에서 실패하는가?",
            "결제 수단별 실패율",
            xaxis_title="Payment Method",
            yaxis_title="Failure Rate (%)",
        ),
    )


def _layout(title, subtitle, **kwargs):
    layout = {
        "title": {"text": f"{title}<br><sup>{subtitle}</sup>", "x": 0.02},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "font": {"family": "Arial, sans-serif", "size": 13},
        "margin": {"l": 60, "r": 30, "t": 78, "b": 55},
        "legend": {"orientation": "h", "y": -0.2},
    }
    layout.update(kwargs)
    return layout


def kpi_card(label, value, suffix=""):
    return html.Div(
        [
            html.Div(label, className="kpi-label"),
            html.Div(f"{value:,}{suffix}", className="kpi-value"),
        ],
        className="kpi-card",
    )


def build_layout():
    kpis = fetch_kpis()
    return html.Div(
        [
            html.Header(
                [
                    html.H1("이벤트 로그 분석 대시보드"),
                    html.P("README의 분석 질문에 맞춰 방문, 유입, 전환, 결제 실패를 확인합니다."),
                ],
                className="header",
            ),
            html.Section(
                [
                    kpi_card("방문 시작", kpis["visits"]),
                    kpi_card("콘텐츠 상세 조회", kpis["content_views"]),
                    kpi_card("구매 완료", kpis["purchases"]),
                    kpi_card("매출", kpis["revenue"], "원"),
                    kpi_card("상세 이동률", kpis["content_view_rate"], "%"),
                    kpi_card("조회→구매율", kpis["purchase_rate"], "%"),
                    kpi_card("결제 실패율", kpis["payment_failure_rate"], "%"),
                ],
                className="kpi-grid",
            ),
            html.Main(
                [
                    dcc.Graph(figure=partner_visit_figure(), className="chart"),
                    dcc.Graph(figure=utm_source_figure(), className="chart"),
                    dcc.Graph(figure=partner_funnel_figure(), className="chart chart-wide"),
                    dcc.Graph(figure=content_conversion_figure(), className="chart chart-wide"),
                    dcc.Graph(figure=payment_failure_figure(), className="chart"),
                ],
                className="dashboard-grid",
            ),
        ],
        className="page",
    )


def create_app():
    app = Dash(__name__)
    app.title = "Event Analytics Dashboard"
    app.layout = build_layout()
    app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    margin: 0;
                    background: #f5f7fb;
                    color: #172033;
                    font-family: Arial, sans-serif;
                }
                .page {
                    max-width: 1440px;
                    margin: 0 auto;
                    padding: 28px;
                }
                .header {
                    margin-bottom: 22px;
                }
                .header h1 {
                    margin: 0 0 8px;
                    font-size: 30px;
                    font-weight: 700;
                }
                .header p {
                    margin: 0;
                    color: #5b6475;
                }
                .kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(7, minmax(120px, 1fr));
                    gap: 12px;
                    margin-bottom: 18px;
                }
                .kpi-card,
                .chart {
                    background: #ffffff;
                    border: 1px solid #e1e6ef;
                    border-radius: 8px;
                }
                .kpi-card {
                    padding: 16px;
                }
                .kpi-label {
                    color: #687387;
                    font-size: 13px;
                    margin-bottom: 8px;
                }
                .kpi-value {
                    font-size: 24px;
                    font-weight: 700;
                }
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 16px;
                }
                .chart-wide {
                    grid-column: span 2;
                }
                @media (max-width: 1000px) {
                    .kpi-grid {
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                    }
                    .dashboard-grid {
                        grid-template-columns: 1fr;
                    }
                    .chart-wide {
                        grid-column: span 1;
                    }
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="대시보드 호스트")
    parser.add_argument("--port", type=int, default=8050, help="대시보드 포트")
    args = parser.parse_args()

    app = create_app()
    app.run_server(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
