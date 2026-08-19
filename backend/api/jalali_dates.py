"""Jalali (Iranian) calendar helpers for warehouse SQL prompts."""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional

_MONTHS: tuple[str, ...] = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)
_MONTH_INDEX = {name: i + 1 for i, name in enumerate(_MONTHS)}
_YEAR_RE = re.compile(r"\b(13|14)\d{2}\b")
_MONTH_YEAR_RE = re.compile(
    r"(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)"
    r"\s+(13\d{2}|14\d{2})"
)
_YEAR_MONTH_RE = re.compile(
    r"(13\d{2}|14\d{2})\s+"
    r"(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)"
)


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Convert a Jalali date to Gregorian (year, month, day)."""
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm < 13 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


def jalali_month_gregorian_bounds(jy: int, jm: int) -> tuple[dt.date, dt.date]:
    """Inclusive start and exclusive end (next day after last Jalali day)."""
    gy, gm, gd = jalali_to_gregorian(jy, jm, 1)
    start = dt.date(gy, gm, gd)
    if jm == 12:
        ny, nm = jy + 1, 1
    else:
        ny, nm = jy, jm + 1
    ey, em, ed = jalali_to_gregorian(ny, nm, 1)
    end = dt.date(ey, em, ed)
    return start, end


def _first_jalali_year(prompt: str) -> Optional[int]:
    match = _YEAR_RE.search(prompt or "")
    if not match:
        return None
    return int(match.group(0))


def _first_jalali_month_year(prompt: str) -> Optional[tuple[int, int]]:
    text = prompt or ""
    match = _MONTH_YEAR_RE.search(text) or _YEAR_MONTH_RE.search(text)
    if not match:
        return None
    a, b = match.group(1), match.group(2)
    if a in _MONTH_INDEX:
        return _MONTH_INDEX[a], int(b)
    return _MONTH_INDEX[b], int(a)


def calendar_hint_for_prompt(prompt: str) -> str:
    """SQL filter text so Jalali month/year prompts do not scan Gregorian year 1405."""
    text = prompt or ""
    year = _first_jalali_year(text)
    if year is None:
        return ""
    lines = [
        "Warehouse calendar (required for this prompt):",
        f"- Sales.DarkhastFaktor.Sal is the Jalali year. Filter Sal = {year}.",
        "- Sales.DarkhastFaktor.TarikhFaktor is Gregorian datetime. "
        f"Never YEAR(TarikhFaktor) = {year} and never date literals like "
        f"'{year}-04-01' (out of SQL Server datetime range).",
        "- Do not wrap TarikhFaktor in YEAR/MONTH/DATENAME in WHERE.",
    ]
    month_year = _first_jalali_month_year(text)
    if month_year:
        jm, jy = month_year
        start, end = jalali_month_gregorian_bounds(jy, jm)
        month_name = _MONTHS[jm - 1]
        lines.append(
            f"- {month_name} {jy} inclusive range: "
            f"TarikhFaktor >= '{start.isoformat()}' AND "
            f"TarikhFaktor < '{end.isoformat()}'."
        )
    if "کرمان" in text:
        lines.append(
            "- Center names: Global.MarkazPakhsh (NameMarkazPakhsh, ccMarkazPakhsh). "
            "Exact N'کرمان' is not N'کرمانشاه'."
        )
    return "\n".join(lines)
