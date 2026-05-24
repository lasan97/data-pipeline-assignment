import argparse

import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from src.dashboard.common import fetch_kpis, fetch_partner_options, figure_layout
from src.dashboard.overview import (
    content_sales_ranking_figure,
    partner_conversion_figure,
    partner_sales_ranking_figure,
    payment_failure_figure,
    utm_source_figure,
)
from src.dashboard.partner import (
    partner_channel_figure,
    partner_content_figure,
    partner_content_sales_figure,
    partner_funnel_figure_for,
    partner_payment_figure,
)


def kpi_card(label, value, suffix=""):
    return html.Div(
        [
            html.Div(label, className="kpi-label"),
            html.Div(f"{value:,}{suffix}", className="kpi-value"),
        ],
        className="kpi-card",
    )


def kpi_cards(kpis, total_prefix=False):
    prefix = "총 " if total_prefix else ""

    return [
        kpi_card(f"{prefix}유입", kpis["visits"]),
        kpi_card(f"{prefix}콘텐츠 상세 조회", kpis["content_views"]),
        kpi_card(f"{prefix}구매 완료", kpis["purchases"]),
        kpi_card(f"{prefix}매출", kpis["revenue"], "원"),
        kpi_card(f"{prefix}상세 이동률", kpis["content_view_rate"], "%"),
        kpi_card(f"{prefix}조회→구매율", kpis["purchase_rate"], "%"),
        kpi_card(f"{prefix}결제 실패율", kpis["payment_failure_rate"], "%"),
    ]


def build_layout():
    kpis = fetch_kpis()
    partner_options = fetch_partner_options()
    default_partner = partner_options[0]["value"] if partner_options else None

    return html.Div(
        [
            html.Header(
                [
                    html.H1("이벤트 로그 분석 대시보드"),
                    html.P("플랫폼 전체 흐름과 파트너별 컨설팅 지표를 확인합니다."),
                ],
                className="header",
            ),
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="대시보드",
                        value="overview",
                        children=[
                            html.Section(kpi_cards(kpis, total_prefix=True), className="kpi-grid"),
                            html.Main(
                                [
                                    dcc.Graph(figure=utm_source_figure(), className="chart"),
                                    dcc.Graph(
                                        figure=partner_conversion_figure(),
                                        className="chart chart-wide",
                                    ),
                                    dcc.Graph(
                                        figure=partner_sales_ranking_figure(),
                                        className="chart chart-wide",
                                    ),
                                    dcc.Graph(
                                        figure=content_sales_ranking_figure(),
                                        className="chart chart-wide",
                                    ),
                                    dcc.Graph(
                                        figure=payment_failure_figure(),
                                        className="chart chart-wide",
                                    ),
                                ],
                                className="dashboard-grid",
                            ),
                        ],
                        className="tab",
                        selected_className="tab-selected",
                    ),
                    dcc.Tab(
                        label="파트너",
                        value="partner",
                        children=[
                            html.Div(
                                [
                                    html.Label("파트너 선택", htmlFor="partner-select"),
                                    dcc.Dropdown(
                                        id="partner-select",
                                        options=partner_options,
                                        value=default_partner,
                                        clearable=False,
                                    ),
                                ],
                                className="filter-row",
                            ),
                            html.Section(id="partner-kpis", className="kpi-grid"),
                            html.Main(
                                [
                                    dcc.Graph(id="partner-funnel", className="chart chart-wide"),
                                    dcc.Graph(id="partner-channel", className="chart"),
                                    dcc.Graph(
                                        id="partner-content",
                                        className="chart chart-wide",
                                    ),
                                    dcc.Graph(
                                        id="partner-content-sales",
                                        className="chart chart-wide",
                                    ),
                                    dcc.Graph(id="partner-payment", className="chart chart-wide"),
                                ],
                                className="dashboard-grid",
                            ),
                        ],
                        className="tab",
                        selected_className="tab-selected",
                    ),
                ],
                value="overview",
                className="tabs",
            ),
        ],
        className="page",
    )


def create_app():
    app = Dash(__name__)
    app.title = "Event Analytics Dashboard"
    app.layout = build_layout()

    @app.callback(
        Output("partner-kpis", "children"),
        Output("partner-funnel", "figure"),
        Output("partner-channel", "figure"),
        Output("partner-content", "figure"),
        Output("partner-content-sales", "figure"),
        Output("partner-payment", "figure"),
        Input("partner-select", "value"),
    )
    def update_partner_tab(partner_id):
        if not partner_id:
            empty = go.Figure(
                layout=figure_layout("파트너 데이터 없음", "파트너 seed 데이터가 필요합니다.")
            )
            return [], empty, empty, empty, empty, empty

        return (
            kpi_cards(fetch_kpis(partner_id)),
            partner_funnel_figure_for(partner_id),
            partner_channel_figure(partner_id),
            partner_content_figure(partner_id),
            partner_content_sales_figure(partner_id),
            partner_payment_figure(partner_id),
        )

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
                .tabs {
                    margin-top: 18px;
                }
                .tab {
                    border: 1px solid #d9e0ea !important;
                    border-bottom: none !important;
                    background: #eef2f7 !important;
                    color: #687387 !important;
                    padding: 12px 18px !important;
                    font-weight: 700;
                }
                .tab-selected {
                    background: #ffffff !important;
                    color: #172033 !important;
                    border-top: 3px solid #4C78A8 !important;
                }
                .filter-row {
                    display: grid;
                    grid-template-columns: 160px minmax(260px, 420px);
                    gap: 12px;
                    align-items: center;
                    background: #ffffff;
                    border: 1px solid #e1e6ef;
                    border-radius: 8px;
                    padding: 16px;
                    margin: 18px 0;
                }
                .filter-row label {
                    color: #445066;
                    font-weight: 700;
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
                    .filter-row {
                        grid-template-columns: 1fr;
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
