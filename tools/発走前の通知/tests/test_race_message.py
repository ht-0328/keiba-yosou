"""RaceMessage（保存した予想から通知の文と添付を作る）のテスト。予想の値は架空。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.race_plan import PlacePick, RacePlan
from 今週の予想.tests.test_forecast_store import sample_forecast

from 発走前の通知.race_message import RaceMessage

RID = "2025041905010101"


def test_文は印から始まり添付は全頭の予想根拠(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    store.save(sample_forecast(RID))
    notice = RaceMessage(store).build(RID)
    assert notice.text.startswith("### 2025-04-19（土） 東京 1R")
    assert "◎" in notice.text
    assert notice.attachment == tmp_path / "2025-04-19" / f"{RID}.md"


def test_計画があれば複勝の金額が文に入る(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    forecast = sample_forecast(RID)
    plan = RacePlan(RID, forecast["title"], "前日", "勝負", "見込みの利益が大きい", 0.3, 1.05, False,
                    picks=(PlacePick(3, 0.42, 1.05, 1.5, 1200),), budget_yen=1200)
    forecast["plan"] = plan.to_dict()
    store.save(forecast)
    assert "1,200円" in RaceMessage(store).build(RID).text


def test_予想が無ければ止まる(tmp_path: Path) -> None:
    with pytest.raises(LookupError, match=RID):
        RaceMessage(ForecastStore(tmp_path)).build(RID)
