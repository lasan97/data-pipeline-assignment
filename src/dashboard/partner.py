import plotly.graph_objects as go

from src.dashboard.common import CHANNEL_COLORS, fetch_rows, figure_layout, payment_status_figure


def partner_funnel_figure_for(partner_id):
    rows = fetch_rows(
        """
        SELECT
            DATE_TRUNC('hour', occurred_at AT TIME ZONE 'Asia/Seoul') AS hour_start,
            TO_CHAR(
                DATE_TRUNC('hour', occurred_at AT TIME ZONE 'Asia/Seoul'),
                'MM-DD HH24:00'
            ) AS hour,
            COUNT(*) AS event_count
        FROM events
        WHERE partner_id = %s
        GROUP BY hour_start, hour
        ORDER BY hour_start
        """,
        (partner_id,),
    )
    return go.Figure(
        data=[
            go.Scatter(
                name="이벤트 수",
                x=[row[1] for row in rows],
                y=[row[2] for row in rows],
                mode="lines+markers",
                line={"color": "#4C78A8", "width": 3},
                marker={"size": 7},
                hovertemplate="시간=%{x}<br>이벤트 수=%{y}<extra></extra>",
            )
        ],
        layout=figure_layout(
            "시간대별 이벤트 추이",
            None,
            xaxis_title="시간",
            yaxis_title="이벤트 수",
        ),
    )


def partner_content_figure(partner_id):
    rows = fetch_rows(
        """
        WITH content_events AS (
            SELECT
                properties->>'content_id' AS content_id,
                COUNT(*) FILTER (WHERE event_type = 'content_view') AS views,
                COUNT(*) FILTER (WHERE event_type = 'purchase_start') AS starts,
                COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
                COALESCE(SUM((properties->>'amount')::integer) FILTER (
                    WHERE event_type = 'purchase_complete'
                ), 0) AS revenue
            FROM events
            WHERE partner_id = %s
              AND event_type IN ('content_view', 'purchase_start', 'purchase_complete')
            GROUP BY properties->>'content_id'
        )
        SELECT
            contents.content_title,
            COALESCE(content_events.views, 0) AS views,
            COALESCE(content_events.starts, 0) AS starts,
            COALESCE(content_events.purchases, 0) AS purchases,
            COALESCE(content_events.revenue, 0) AS revenue,
            ROUND(
                COALESCE(content_events.starts, 0)::numeric
                / NULLIF(COALESCE(content_events.views, 0), 0)
                * 100,
                1
            ) AS purchase_start_rate,
            ROUND(
                COALESCE(content_events.purchases, 0)::numeric
                / NULLIF(COALESCE(content_events.views, 0), 0)
                * 100,
                1
            ) AS purchase_complete_rate
        FROM contents
        LEFT JOIN content_events ON content_events.content_id = contents.content_id
        WHERE contents.partner_id = %s
        ORDER BY purchase_complete_rate DESC NULLS LAST, purchase_start_rate DESC NULLS LAST
        """,
        (partner_id, partner_id),
    )
    contents = [row[0] for row in rows]

    return go.Figure(
        data=[
            go.Bar(
                name="조회→구매 시작률",
                x=contents,
                y=[float(row[5] or 0) for row in rows],
                marker_color="#72B7B2",
                customdata=[[row[1], row[2]] for row in rows],
                hovertemplate=(
                    "조회 수=%{customdata[0]}<br>"
                    "구매 시작=%{customdata[1]}<br>"
                    "구매 시작률=%{y}%<extra></extra>"
                ),
            ),
            go.Bar(
                name="조회→구매 완료율",
                x=contents,
                y=[float(row[6] or 0) for row in rows],
                marker_color="#54A24B",
                customdata=[[row[1], row[2], row[3], row[4]] for row in rows],
                hovertemplate=(
                    "조회 수=%{customdata[0]}<br>"
                    "구매 시작=%{customdata[1]}<br>"
                    "구매 완료=%{customdata[2]}<br>"
                    "매출=%{customdata[3]:,}원<br>"
                    "구매 완료율=%{y}%<extra></extra>"
                ),
            ),
        ],
        layout=figure_layout(
            "콘텐츠별 구매 전환율",
            None,
            xaxis_title="콘텐츠",
            yaxis_title="전환율 (%)",
            barmode="group",
        ),
    )


def partner_content_sales_figure(partner_id):
    rows = fetch_rows(
        """
        SELECT
            contents.content_title,
            COUNT(events.event_id) AS sales_count,
            COALESCE(SUM((events.properties->>'amount')::integer), 0) AS revenue
        FROM contents
        JOIN events
          ON events.properties->>'content_id' = contents.content_id
         AND events.event_type = 'purchase_complete'
        WHERE contents.partner_id = %s
        GROUP BY contents.content_id, contents.content_title
        ORDER BY sales_count DESC, revenue DESC
        LIMIT 10
        """,
        (partner_id,),
    )
    contents = [row[0] for row in rows]

    return go.Figure(
        data=[
            go.Bar(
                name="판매량",
                x=[row[1] for row in rows],
                y=contents,
                orientation="h",
                marker_color="#54A24B",
                offsetgroup="sales_count",
                alignmentgroup="partner_content_metric",
                hovertemplate="판매량=%{x}<extra></extra>",
            ),
            go.Bar(
                name="매출",
                x=[row[2] for row in rows],
                y=contents,
                orientation="h",
                xaxis="x2",
                marker_color="#F58518",
                offsetgroup="revenue",
                alignmentgroup="partner_content_metric",
                hovertemplate="매출=%{x:,}원<extra></extra>",
            ),
        ],
        layout=figure_layout(
            "콘텐츠별 판매량·매출 Top 10",
            None,
            xaxis={"title": "판매량"},
            xaxis2={
                "title": "매출",
                "overlaying": "x",
                "side": "top",
                "showgrid": False,
            },
            yaxis={"title": "", "autorange": "reversed"},
            barmode="group",
            legend={"orientation": "h", "y": -0.2},
        ),
    )


def partner_channel_figure(partner_id):
    rows = fetch_rows(
        """
        WITH landing AS (
            SELECT
                session_id,
                COALESCE(properties->>'utm_source', 'none') AS utm_source
            FROM events
            WHERE partner_id = %s
              AND event_type = 'landing_page_view'
        ),
        purchases AS (
            SELECT DISTINCT session_id
            FROM events
            WHERE partner_id = %s
              AND event_type = 'purchase_complete'
        )
        SELECT
            landing.utm_source,
            COUNT(*) AS visit_count,
            COUNT(purchases.session_id) AS purchase_count,
            ROUND(
                COUNT(purchases.session_id)::numeric / NULLIF(COUNT(*), 0) * 100,
                1
            ) AS purchase_rate
        FROM landing
        LEFT JOIN purchases ON purchases.session_id = landing.session_id
        GROUP BY landing.utm_source
        ORDER BY purchase_rate DESC NULLS LAST, visit_count DESC
        """,
        (partner_id, partner_id),
    )
    labels = [row[0] for row in rows]
    colors = [CHANNEL_COLORS.get(label, "#72B7B2") for label in labels]

    return go.Figure(
        data=[
            go.Pie(
                name="유입 비중",
                labels=labels,
                values=[row[1] for row in rows],
                hole=0.35,
                marker={"colors": colors},
                sort=False,
                direction="clockwise",
                domain={"x": [0.0, 0.45], "y": [0.0, 1.0]},
                textinfo="label+percent",
                hovertemplate="유입 채널=%{label}<br>유입=%{value}<extra></extra>",
            ),
            go.Bar(
                name="구매율",
                x=labels,
                y=[float(row[3] or 0) for row in rows],
                marker_color=colors,
                xaxis="x2",
                yaxis="y2",
                showlegend=False,
                text=[f"{float(row[3] or 0):.1f}%" for row in rows],
                textposition="auto",
                customdata=[[row[1], row[2]] for row in rows],
                hovertemplate=(
                    "유입=%{customdata[0]}<br>"
                    "구매 완료=%{customdata[1]}<br>"
                    "구매율=%{y}%<extra></extra>"
                ),
            ),
        ],
        layout=figure_layout(
            "유입 채널별 방문 비중·구매율",
            "왼쪽은 유입 비중, 오른쪽은 구매율",
            showlegend=True,
            xaxis2={"domain": [0.55, 1.0], "title": "유입 채널"},
            yaxis2={"domain": [0.0, 1.0], "title": "구매율 (%)", "range": [0, 100]},
            annotations=[
                {
                    "text": "유입 비중",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.225,
                    "y": 1.08,
                    "showarrow": False,
                },
                {
                    "text": "구매율",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.775,
                    "y": 1.08,
                    "showarrow": False,
                },
            ],
        ),
    )


def partner_payment_figure(partner_id):
    return payment_status_figure(partner_id)
