"""Demo result payload mirroring the frontend preview."""

from __future__ import annotations


def get_demo_result(mode: str) -> dict:
    echarts_option = {
        "color": ["#3d9b82", "#5cb89a", "#7ab89f"],
        "backgroundColor": "transparent",
        "title": {
            "text": "Revenue by region",
            "left": "center",
            "textStyle": {"color": "#e6ebe9", "fontWeight": 600, "fontSize": 16},
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "#24302d",
            "borderColor": "#3a4a45",
            "textStyle": {"color": "#e6ebe9"},
        },
        "grid": {"left": 48, "right": 24, "top": 56, "bottom": 40},
        "xAxis": {
            "type": "category",
            "data": ["North", "South", "East", "West"],
            "axisLabel": {"color": "#9aada6"},
            "axisLine": {"lineStyle": {"color": "#3a4a45"}},
        },
        "yAxis": {
            "type": "value",
            "name": "USD",
            "nameTextStyle": {"color": "#9aada6"},
            "axisLabel": {"color": "#9aada6"},
            "splitLine": {"lineStyle": {"color": "#3a4a45"}},
            "axisLine": {"lineStyle": {"color": "#3a4a45"}},
        },
        "series": [
            {
                "name": "Revenue",
                "type": "bar",
                "data": [420, 310, 510, 280],
                "barWidth": "48%",
                "itemStyle": {"borderRadius": [6, 6, 0, 0]},
            }
        ],
    }

    text_report = (
        "North and East lead revenue this period. East is highest at 510; West trails at 280. "
        "Focus follow-up on West conversion and East capacity. (Demo sample — orchestration stub.)"
    )

    if mode == "analysis":
        return {"mode": mode, "text_report": text_report, "echarts_option": None}
    if mode == "chart":
        return {"mode": mode, "text_report": None, "echarts_option": echarts_option}
    return {"mode": "both", "text_report": text_report, "echarts_option": echarts_option}
