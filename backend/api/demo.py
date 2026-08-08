"""Demo result payload mirroring the frontend preview."""

from __future__ import annotations


def get_demo_result(mode: str) -> dict:
    echarts_option = {
        "color": ["#1f6f5b", "#3d8b74", "#7ab89f"],
        "title": {
            "text": "Revenue by region",
            "left": "center",
            "textStyle": {"color": "#0f1c1a", "fontWeight": 600, "fontSize": 16},
        },
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 24, "top": 56, "bottom": 40},
        "xAxis": {
            "type": "category",
            "data": ["North", "South", "East", "West"],
            "axisLabel": {"color": "#5c6f69"},
        },
        "yAxis": {
            "type": "value",
            "name": "USD",
            "axisLabel": {"color": "#5c6f69"},
            "splitLine": {"lineStyle": {"color": "#c9d6d0"}},
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
