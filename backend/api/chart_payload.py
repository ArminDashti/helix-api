"""Build ECharts options and grids from fetched SQL rows."""

from __future__ import annotations

from typing import Any


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", ""))
            return True
        except ValueError:
            return False
    return False


def _as_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(str(value).replace(",", ""))


def build_grid(fetch: dict[str, Any], columns: list[str] | None = None) -> dict[str, Any]:
    cols = [c for c in (columns or fetch.get("columns") or []) if c]
    if not cols:
        cols = list(fetch.get("columns") or [])
    rows = []
    for row in fetch.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if cols:
            rows.append({col: row.get(col) for col in cols})
        else:
            rows.append(row)
    return {"columns": cols, "rows": rows}


def build_echarts_option(
    fetch: dict[str, Any],
    *,
    chart_type: str = "bar",
    language: str = "en",
) -> dict[str, Any] | None:
    rows = [r for r in (fetch.get("rows") or []) if isinstance(r, dict)]
    columns = list(fetch.get("columns") or [])
    if not rows or not columns:
        return None
    cat_col = next((c for c in columns if not _is_number(rows[0].get(c))), columns[0])
    num_cols = [c for c in columns if c != cat_col and any(_is_number(r.get(c)) for r in rows)]
    if not num_cols:
        return None
    categories = [str(r.get(cat_col) if r.get(cat_col) is not None else "") for r in rows]
    series_name = num_cols[0]
    values = [_as_number(r.get(series_name) or 0) for r in rows]
    title = "نتایج" if language == "fa" else "Query results"
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
                "data": [{"name": n, "value": v} for n, v in zip(categories, values)],
                "label": {"color": "#e6ebe9"},
            }
        ]
        return base
    category_axis = {
        "type": "category",
        "data": categories,
        "axisLabel": {"color": "#c5d0cc"},
        "axisLine": {"lineStyle": {"color": "#3a4a45"}},
    }
    value_axis = {
        "type": "value",
        "axisLabel": {"color": "#c5d0cc"},
        "splitLine": {"lineStyle": {"color": "#2c3a36"}},
    }
    if chart_type == "horizontal_bar":
        base["xAxis"] = value_axis
        base["yAxis"] = category_axis
        series_type = "bar"
    else:
        base["xAxis"] = category_axis
        base["yAxis"] = value_axis
        series_type = "line" if chart_type in ("line", "area") else "scatter" if chart_type == "scatter" else "bar"
    series: dict[str, Any] = {
        "name": series_name,
        "type": series_type,
        "data": values,
        "itemStyle": {"color": colors[0]},
    }
    if chart_type == "area":
        series["areaStyle"] = {"opacity": 0.25}
    if chart_type == "stacked_bar":
        series["stack"] = "total"
        extra = []
        for name in num_cols[1:3]:
            extra.append(
                {
                    "name": name,
                    "type": "bar",
                    "stack": "total",
                    "data": [_as_number(r.get(name) or 0) for r in rows],
                }
            )
        base["legend"] = {"textStyle": {"color": "#c5d0cc"}}
        base["series"] = [series, *extra]
        return base
    base["series"] = [series]
    return base
