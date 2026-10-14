"""登録日相当（材料の締めの日）の決め方（設計書 06 の図3）。Python の関数と SQL の式が同じ答えを出すこと。"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pytest

from ..dataset import RegistrationCutoff


@pytest.mark.parametrize(("race_day", "expected"), [
    (date(2026, 10, 17), date(2026, 10, 12)),  # 土曜 → 5日前の月曜
    (date(2026, 10, 18), date(2026, 10, 12)),  # 日曜 → 6日前の月曜
    (date(2026, 10, 12), date(2026, 10, 5)),   # 月曜（祝日の開催）→ 前の週の月曜
    (date(2026, 10, 14), date(2026, 10, 12)),  # 水曜 → 2日前の月曜
])
def test_the_cutoff_is_the_latest_monday_before_the_race_day(race_day: date, expected: date):
    assert RegistrationCutoff().of(race_day) == expected
    assert expected.isoweekday() == 1 and expected < race_day


def test_the_sql_expression_agrees_with_the_python_function():
    cutoff = RegistrationCutoff()
    days = [date(2026, 1, 1) + timedelta(days=offset) for offset in range(21)]
    values = ", ".join(f"('{day.isoformat()}')" for day in days)
    rows = duckdb.sql(f"SELECT {cutoff.sql('day')} FROM (VALUES {values}) AS t(day) ORDER BY day").fetchall()
    assert [row[0] for row in rows] == [cutoff.of(day) for day in days]
