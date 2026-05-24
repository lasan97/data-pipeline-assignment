import plotly.graph_objects as go

from src.dashboard.common import CHANNEL_COLORS, fetch_rows, figure_layout, payment_status_figure


def utm_source_figure():
    rows = fetch_rows(
        """
        WITH landing AS (
            SELECT
                session_id,
                COALESCE(properties->>'utm_source', 'none') AS utm_source
            FROM events
            WHERE event_type = 'landing_page_view'
        ),
        purchases AS (
            SELECT DISTINCT session_id
            FROM events
            WHERE event_type = 'purchase_complete'
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
        """
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


def partner_conversion_figure():
    rows = fetch_rows(
        """
        SELECT
            partner_id,
            COUNT(*) FILTER (WHERE event_type = 'session_start') AS visits,
            COUNT(*) FILTER (WHERE event_type = 'content_view') AS content_views,
            COUNT(*) FILTER (WHERE event_type = 'purchase_complete') AS purchases,
            ROUND(
                COUNT(*) FILTER (WHERE event_type = 'content_view')::numeric
                / NULLIF(COUNT(*) FILTER (WHERE event_type = 'session_start'), 0)
                * 100,
                1
            ) AS content_view_rate,
            ROUND(
                COUNT(*) FILTER (WHERE event_type = 'purchase_complete')::numeric
                / NULLIF(COUNT(*) FILTER (WHERE event_type = 'content_view'), 0)
                * 100,
                1
            ) AS purchase_rate
        FROM events
        GROUP BY partner_id
        ORDER BY purchase_rate DESC NULLS LAST, content_view_rate DESC NULLS LAST
        """
    )
    partners = [row[0] for row in rows]

    return go.Figure(
        data=[
            go.Bar(
                name="유입→콘텐츠 조회율",
                x=partners,
                y=[float(row[4] or 0) for row in rows],
                marker_color="#72B7B2",
                customdata=[[row[1], row[2]] for row in rows],
                hovertemplate=(
                    "유입=%{customdata[0]}<br>"
                    "콘텐츠 조회=%{customdata[1]}<br>"
                    "조회율=%{y}%<extra></extra>"
                ),
            ),
            go.Bar(
                name="콘텐츠 조회→구매 완료율",
                x=partners,
                y=[float(row[5] or 0) for row in rows],
                marker_color="#54A24B",
                customdata=[[row[2], row[3]] for row in rows],
                hovertemplate=(
                    "콘텐츠 조회=%{customdata[0]}<br>"
                    "구매 완료=%{customdata[1]}<br>"
                    "구매율=%{y}%<extra></extra>"
                ),
            ),
        ],
        layout=figure_layout(
            "파트너별 전환율 비교",
            "유입→콘텐츠 조회율, 콘텐츠 조회→구매 완료율",
            xaxis_title="파트너",
            yaxis_title="전환율 (%)",
            barmode="group",
        ),
    )


def partner_sales_ranking_figure():
    rows = fetch_rows(
        """
        SELECT
            partner_id,
            COUNT(*) AS sales_count,
            COALESCE(SUM((properties->>'amount')::integer) FILTER (
                WHERE event_type = 'purchase_complete'
            ), 0) AS revenue
        FROM events
        WHERE event_type = 'purchase_complete'
        GROUP BY partner_id
        ORDER BY sales_count DESC, revenue DESC
        LIMIT 10
        """
    )
    partners = [row[0] for row in rows]

    return go.Figure(
        data=[
            go.Bar(
                name="판매량",
                x=[row[1] for row in rows],
                y=partners,
                orientation="h",
                marker_color="#54A24B",
                offsetgroup="sales_count",
                alignmentgroup="partner_metric",
                textposition="auto",
                hovertemplate="판매량=%{x}<extra></extra>",
            ),
            go.Bar(
                name="매출",
                x=[row[2] for row in rows],
                y=partners,
                orientation="h",
                xaxis="x2",
                marker_color="#F58518",
                offsetgroup="revenue",
                alignmentgroup="partner_metric",
                hovertemplate="매출=%{x:,}원<extra></extra>",
            ),
        ],
        layout=figure_layout(
            "파트너별 판매량·매출 Top 10",
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


def content_sales_ranking_figure():
    rows = fetch_rows(
        """
        SELECT
            contents.content_title,
            contents.partner_id,
            COUNT(events.event_id) AS sales_count,
            COALESCE(SUM((events.properties->>'amount')::integer), 0) AS revenue
        FROM contents
        JOIN events
          ON events.properties->>'content_id' = contents.content_id
         AND events.event_type = 'purchase_complete'
        GROUP BY contents.content_id, contents.content_title, contents.partner_id
        ORDER BY sales_count DESC, revenue DESC
        LIMIT 10
        """
    )
    labels = [f"{row[0]}<br><sup>{row[1]}</sup>" for row in rows]

    return go.Figure(
        data=[
            go.Bar(
                name="판매량",
                x=[row[2] for row in rows],
                y=labels,
                orientation="h",
                marker_color="#54A24B",
                offsetgroup="sales_count",
                alignmentgroup="content_metric",
                textposition="auto",
                hovertemplate="판매량=%{x}<extra></extra>",
            ),
            go.Bar(
                name="매출",
                x=[row[3] for row in rows],
                y=labels,
                orientation="h",
                xaxis="x2",
                marker_color="#F58518",
                offsetgroup="revenue",
                alignmentgroup="content_metric",
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


def payment_failure_figure():
    return payment_status_figure()
