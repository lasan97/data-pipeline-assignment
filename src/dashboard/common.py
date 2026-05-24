import plotly.graph_objects as go
import psycopg

from src.event_generator import database_url_from_env, load_dotenv


CHANNEL_COLORS = {
    "google": "#4C78A8",
    "naver": "#54A24B",
    "instagram": "#E45756",
    "newsletter": "#F58518",
    "none": "#9D9DA1",
}

DEVICE_COLORS = {
    "desktop": "#4C78A8",
    "mobile": "#F58518",
    "tablet": "#54A24B",
}


def fetch_rows(query, params=None):
    load_dotenv()
    with psycopg.connect(database_url_from_env()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def fetch_kpis(partner_id=None):
    where_clause = ""
    params = ()
    if partner_id:
        where_clause = "WHERE partner_id = %s"
        params = (partner_id,)

    rows = fetch_rows(
        f"""
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
        {where_clause}
        """,
        params,
    )
    row = rows[0]
    visits = row[0] or 0
    content_views = row[1] or 0
    purchases = row[3] or 0
    payment_failures = row[4] or 0
    revenue = row[5] or 0

    return {
        "visits": visits,
        "content_views": content_views,
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


def fetch_partner_options():
    rows = fetch_rows(
        """
        SELECT partner_id, partner_name
        FROM partners
        ORDER BY partner_id
        """
    )
    return [
        {"label": f"{partner_name} ({partner_id})", "value": partner_id}
        for partner_id, partner_name in rows
    ]


def figure_layout(title, subtitle, **kwargs):
    title_text = title if subtitle is None else f"{title}<br><sup>{subtitle}</sup>"
    layout = {
        "title": {"text": title_text, "x": 0.02},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "font": {"family": "Arial, sans-serif", "size": 13},
        "margin": {"l": 60, "r": 30, "t": 78, "b": 55},
        "legend": {"orientation": "h", "y": -0.2},
    }
    layout.update(kwargs)
    return layout


def payment_status_figure(partner_id=None):
    params = ()
    if partner_id:
        params = (partner_id,)

    rows = fetch_rows(
        f"""
        WITH payment_events AS (
            SELECT
                properties->>'payment_method' AS payment_method,
                device_type,
                event_type
            FROM events
            WHERE event_type IN ('purchase_complete', 'payment_failed')
            {f"AND partner_id = %s" if partner_id else ""}
        ),
        method_totals AS (
            SELECT
                payment_method,
                COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
                COUNT(*) FILTER (WHERE event_type = 'payment_failed') AS failures,
                ROUND(
                    COUNT(*) FILTER (WHERE event_type = 'payment_failed')::numeric
                    / NULLIF(COUNT(*), 0)
                    * 100,
                    1
                ) AS failure_rate
            FROM payment_events
            GROUP BY payment_method
        ),
        device_totals AS (
            SELECT
                payment_method,
                device_type,
                COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
                COUNT(*) FILTER (WHERE event_type = 'payment_failed') AS failures
            FROM payment_events
            GROUP BY payment_method, device_type
        )
        SELECT
            device_totals.payment_method,
            device_totals.device_type,
            device_totals.purchases,
            device_totals.failures,
            method_totals.failure_rate,
            method_totals.failures AS total_failures
        FROM device_totals
        JOIN method_totals
          ON method_totals.payment_method = device_totals.payment_method
        ORDER BY method_totals.failure_rate DESC NULLS LAST,
                 method_totals.failures DESC,
                 device_totals.payment_method,
                 device_totals.device_type
        """,
        params,
    )
    payment_methods = []
    for row in rows:
        if row[0] not in payment_methods:
            payment_methods.append(row[0])

    category_methods = []
    category_statuses = []
    for payment_method in payment_methods:
        category_methods.extend([payment_method, payment_method])
        category_statuses.extend(["성공", "실패"])

    device_types = sorted({row[1] for row in rows})
    rows_by_key = {(row[0], row[1]): row for row in rows}
    failure_rates = {row[0]: row[4] for row in rows}
    total_failures = {
        payment_method: sum((row[3] or 0) for row in rows if row[0] == payment_method)
        for payment_method in payment_methods
    }

    traces = []
    for device_type in device_types:
        values = []
        customdata = []
        for payment_method in payment_methods:
            row = rows_by_key.get((payment_method, device_type))
            purchases = row[2] if row else 0
            failures = row[3] if row else 0
            failure_rate = failure_rates.get(payment_method) or 0
            values.extend([purchases, failures])
            customdata.extend(
                [
                    [payment_method, "결제 성공", failure_rate],
                    [payment_method, "결제 실패", failure_rate],
                ]
            )

        traces.append(
            go.Bar(
                name=device_type,
                x=[category_methods, category_statuses],
                y=values,
                marker_color=DEVICE_COLORS.get(device_type, "#9D9DA1"),
                customdata=customdata,
                hovertemplate=(
                    "결제수단=%{customdata[0]}<br>"
                    "상태=%{customdata[1]}<br>"
                    "디바이스=%{fullData.name}<br>"
                    "건수=%{y}<br>"
                    "에러율=%{customdata[2]}%<extra></extra>"
                ),
            )
        )

    failure_rate_text = []
    failure_rate_methods = []
    failure_rate_statuses = []
    failure_rate_y = []
    for payment_method in payment_methods:
        failure_rate_text.append(f"{float(failure_rates.get(payment_method) or 0):.1f}%")
        failure_rate_methods.append(payment_method)
        failure_rate_statuses.append("실패")
        failure_rate_y.append(total_failures[payment_method])

    return go.Figure(
        data=[
            *traces,
            go.Scatter(
                name="에러율",
                x=[failure_rate_methods, failure_rate_statuses],
                y=failure_rate_y,
                mode="text",
                text=failure_rate_text,
                textposition="top center",
                showlegend=False,
                hoverinfo="skip",
            ),
        ],
        layout=figure_layout(
            "결제 수단별 에러율 추이",
            "성공·실패 막대는 디바이스별로 구분",
            xaxis_title="결제 수단 / 상태",
            yaxis_title="결제 수",
            barmode="stack",
            bargap=0.02,
            bargroupgap=0.0,
        ),
    )
