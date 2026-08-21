"""Demo result payload mirroring the frontend preview."""

from __future__ import annotations

from typing import Any

VALID_MODES = frozenset(
    {
        "auto",
        "chart",
        "analytical_report",
        "grid",
        "analytical_report_chart",
        "research",
        # legacy aliases
        "analysis",
        "both",
    }
)
VALID_LANGUAGES = frozenset({"en", "fa"})
VALID_REPORT_TYPES = frozenset(
    {"low", "medium", "high", "deep", "summary", "simple"}
)
VALID_CHART_TYPES = frozenset(
    {
        "bar",
        "line",
        "area",
        "pie",
        "donut",
        "scatter",
        "stacked_bar",
        "horizontal_bar",
    }
)

_REGIONS = ["North", "South", "East", "West"]
_VALUES = [420, 310, 510, 280]
_VALUES_B = [180, 220, 260, 150]


def _normalize_mode(mode: str) -> str:
    if mode in ("analysis", "research"):
        return "analytical_report"
    if mode == "both":
        return "analytical_report_chart"
    return mode


def _normalize_report_type(report_type: str | None) -> str:
    aliases = {"simple": "low", "summary": "medium", "deep": "high"}
    value = aliases.get(report_type or "", report_type or "medium")
    if value not in {"low", "medium", "high"}:
        return "medium"
    return value


def _chart_option(chart_type: str, language: str) -> dict[str, Any]:
    title = "درآمد بر اساس منطقه" if language == "fa" else "Revenue by region"
    cats = (
        ["شمال", "جنوب", "شرق", "غرب"] if language == "fa" else list(_REGIONS)
    )
    series_name = "درآمد" if language == "fa" else "Revenue"
    series_b = "هزینه" if language == "fa" else "Cost"
    colors = ["#3d9b82", "#5cb89a", "#7ab89f"]
    base: dict[str, Any] = {
        "color": colors,
        "backgroundColor": "transparent",
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {"color": "#e6ebe9", "fontWeight": 600, "fontSize": 16},
        },
        "tooltip": {
            "trigger": "item" if chart_type in ("pie", "donut") else "axis",
            "backgroundColor": "#24302d",
            "borderColor": "#3a4a45",
            "textStyle": {"color": "#e6ebe9"},
        },
    }

    if chart_type in ("pie", "donut"):
        base["series"] = [
            {
                "name": series_name,
                "type": "pie",
                "radius": ["42%", "68%"] if chart_type == "donut" else "65%",
                "data": [
                    {"name": n, "value": v} for n, v in zip(cats, _VALUES)
                ],
                "label": {"color": "#e6ebe9"},
            }
        ]
        return base

    if chart_type == "scatter":
        base["grid"] = {"left": 48, "right": 24, "top": 56, "bottom": 40}
        base["xAxis"] = {
            "type": "value",
            "axisLabel": {"color": "#9aada6"},
            "splitLine": {"lineStyle": {"color": "#3a4a45"}},
        }
        base["yAxis"] = {
            "type": "value",
            "axisLabel": {"color": "#9aada6"},
            "splitLine": {"lineStyle": {"color": "#3a4a45"}},
        }
        base["series"] = [
            {
                "name": series_name,
                "type": "scatter",
                "symbolSize": 14,
                "data": [[i * 100 + 50, v] for i, v in enumerate(_VALUES)],
            }
        ]
        return base

    category_axis = {
        "type": "category",
        "data": cats,
        "axisLabel": {"color": "#9aada6"},
        "axisLine": {"lineStyle": {"color": "#3a4a45"}},
    }
    value_axis = {
        "type": "value",
        "name": "USD" if language == "en" else "واحد",
        "nameTextStyle": {"color": "#9aada6"},
        "axisLabel": {"color": "#9aada6"},
        "splitLine": {"lineStyle": {"color": "#3a4a45"}},
        "axisLine": {"lineStyle": {"color": "#3a4a45"}},
    }
    base["grid"] = {"left": 48, "right": 24, "top": 56, "bottom": 40}

    if chart_type == "horizontal_bar":
        base["xAxis"] = value_axis
        base["yAxis"] = category_axis
        base["series"] = [
            {
                "name": series_name,
                "type": "bar",
                "data": list(_VALUES),
                "itemStyle": {"borderRadius": [0, 6, 6, 0]},
            }
        ]
        return base

    base["xAxis"] = category_axis
    base["yAxis"] = value_axis

    if chart_type == "line":
        base["series"] = [
            {
                "name": series_name,
                "type": "line",
                "smooth": True,
                "data": list(_VALUES),
            }
        ]
    elif chart_type == "area":
        base["series"] = [
            {
                "name": series_name,
                "type": "line",
                "smooth": True,
                "areaStyle": {},
                "data": list(_VALUES),
            }
        ]
    elif chart_type == "stacked_bar":
        base["series"] = [
            {
                "name": series_name,
                "type": "bar",
                "stack": "total",
                "data": list(_VALUES),
            },
            {
                "name": series_b,
                "type": "bar",
                "stack": "total",
                "data": list(_VALUES_B),
            },
        ]
    else:
        base["series"] = [
            {
                "name": series_name,
                "type": "bar",
                "data": list(_VALUES),
                "barWidth": "48%",
                "itemStyle": {"borderRadius": [6, 6, 0, 0]},
            }
        ]
    return base


def _text_report(language: str, report_type: str) -> str:
    level = _normalize_report_type(report_type)
    if language == "fa":
        if level == "high":
            return (
                "تحلیل عمیق: شمال و شرق در این دوره بیشترین درآمد را دارند. "
                "شرق با ۵۱۰ در صدر است و غرب با ۲۸۰ عقب‌تر است. "
                "پیشنهاد می‌شود روی نرخ تبدیل غرب و ظرفیت شرق تمرکز شود. "
                "روند فصلی نشان می‌دهد شرق پایدارتر از شمال رشد کرده است. "
                "(نمونه دمو)"
            )
        if level == "medium":
            return (
                "خلاصه: شرق بیشترین درآمد (۵۱۰) و غرب کمترین (۲۸۰) را دارد. "
                "اولویت: بهبود غرب و حفظ ظرفیت شرق. (نمونه دمو)"
            )
        return "شرق ۵۱۰، شمال ۴۲۰، جنوب ۳۱۰، غرب ۲۸۰. (نمونه دمو)"

    if level == "high":
        return (
            "Deep analysis: North and East lead revenue this period. "
            "East is highest at 510; West trails at 280. "
            "Seasonal trend favors East over North for sustained growth. "
            "Focus follow-up on West conversion and East capacity. (Demo sample)"
        )
    if level == "medium":
        return (
            "Summary: East leads at 510; West trails at 280. "
            "Prioritize West conversion and East capacity. (Demo sample)"
        )
    return "East 510, North 420, South 310, West 280. (Demo sample)"


def _grid_payload(columns: list[str] | None, language: str) -> dict[str, Any]:
    default_cols = (
        ["منطقه", "درآمد", "واحد"]
        if language == "fa"
        else ["Region", "Revenue", "Units"]
    )
    cols = [c for c in (columns or []) if c] or default_cols
    # Ensure at least 3 columns for demo rows
    while len(cols) < 3:
        cols.append(f"Col{len(cols) + 1}")
    regions = (
        ["شمال", "جنوب", "شرق", "غرب"] if language == "fa" else list(_REGIONS)
    )
    rows = []
    units = [12, 9, 15, 7]
    for i, region in enumerate(regions):
        row = {cols[0]: region, cols[1]: _VALUES[i], cols[2]: units[i]}
        for extra in cols[3:]:
            row[extra] = "—"
        rows.append(row)
    return {"columns": cols, "rows": rows}


def get_demo_result(
    mode: str,
    *,
    language: str = "en",
    report_type: str | None = None,
    chart_type: str | None = None,
    chart_types: list[str] | None = None,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    mode = _normalize_mode(mode or "auto")
    language = language if language in VALID_LANGUAGES else "en"
    report_type = _normalize_report_type(report_type)
    types: list[str] = []
    if isinstance(chart_types, list):
        for item in chart_types:
            value = str(item or "").strip()
            if value in VALID_CHART_TYPES and value not in types:
                types.append(value)
            if len(types) >= 4:
                break
    if not types:
        single = chart_type if chart_type in VALID_CHART_TYPES else "bar"
        types = [single]
    chart_type = types[0]

    text_report = None
    echarts_option = None
    echarts_options: list[dict[str, Any]] = []
    grid = None

    if mode in ("analytical_report", "analytical_report_chart", "auto"):
        text_report = _text_report(language, report_type)
    if mode in ("chart", "analytical_report_chart", "auto"):
        for ctype in types:
            option = _chart_option(ctype, language)
            echarts_options.append({"chart_type": ctype, "option": option})
        echarts_option = echarts_options[0]["option"] if echarts_options else None
    if mode == "grid":
        grid = _grid_payload(columns, language)

    return {
        "mode": mode,
        "language": language,
        "report_type": report_type if text_report else None,
        "chart_type": chart_type if echarts_option else None,
        "chart_types": [item["chart_type"] for item in echarts_options] or None,
        "text_report": text_report,
        "echarts_option": echarts_option,
        "echarts_options": echarts_options or None,
        "grid": grid,
    }
