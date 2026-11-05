"""LocalRaceMessage（地方の predict の JSON から通知の中身・文・添付の画像を作る）のテスト。予想の値は架空。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_race_message import LocalRaceMessage
from 発走前の通知.scheduled_race import ScheduledRace

COLUMNS = ["順位", "馬番", "馬名", "単勝オッズ", "オッズから見た3着以内率", "複勝的中の確率", "複勝の期待値", "1着になる確率", "単勝の期待値",
           "3着以内に入る確率", "LightGBM", "CatBoost"]
ROWS = [
    [1, 7, "イチバン", 3.0, 0.70, 0.78, 1.10, 0.35, 1.05, 0.78, 0.77, 0.79],
    [2, 4, "ニバン", 2.7, 0.75, 0.71, 0.95, 0.27, 0.74, 0.71, 0.72, 0.70],
    [3, 8, "サンバン", 5.4, 0.55, 0.60, 1.00, 0.15, 0.81, 0.60, 0.61, 0.59],
    [4, 3, "ヨンバン", 14.2, 0.25, 0.34, 1.30, 0.06, 0.80, 0.34, 0.33, 0.35],
    [5, 2, "ゴバン", 18.3, 0.19, 0.29, 0.90, 0.04, 0.64, 0.29, 0.29, 0.29],
    [6, 1, "ロクバン", 40.0, 0.08, 0.10, 0.60, 0.01, 0.40, 0.10, 0.10, 0.10],
    [7, 6, "ナナバン", 80.0, 0.04, 0.05, 0.50, 0.005, 0.40, 0.05, 0.05, 0.05],
    [8, 5, "ハチバン", 150.0, 0.02, 0.02, 0.30, 0.002, 0.30, 0.02, 0.02, 0.02],
]
RID = "2026110547150401"
RACE = ScheduledRace(rid=RID, venue="笠松", number=1, name="", post=datetime(2026, 11, 5, 10, 25))


def _forecast(timing: str) -> dict:
    return {"title": f"{RID}（2026-11-05）の予測: {timing}の時点", "columns": COLUMNS, "rows": [list(row) for row in ROWS], "note": "", "meta": {}}


class _Schedule:
    def read(self, day: str) -> list[ScheduledRace]:
        return [RACE]


class _Frames:
    def read(self, rid: str) -> dict[int, int]:
        return {7: 5, 4: 3}


def test_中身は印の順の全頭と_見出し_買い目() -> None:
    card = LocalRaceMessage().card(_forecast("当日"), RACE, {7: 5})
    assert card.title == "笠松 1R（10:25 発走）"
    assert card.heading == "笠松 1R" and card.post == "10:25 発走" and card.race_day
    assert list(card.table["mark"]) == ["◎", "○", "▲", "△", "△", "△", "☆", "注"]
    assert list(card.table["horse_no"])[:6] == [7, 4, 8, 3, 2, 1]
    assert card.frames == {7: 5}
    assert card.bets.lines == ("単勝 ◎7 イチバン（期待値 1.05）100円", "複勝 3 ヨンバン（期待値 1.30）100円")


def test_文は_見出し_上位の印_買い目だけ() -> None:
    message = LocalRaceMessage()
    text = message.describe(message.card(_forecast("当日"), RACE, {}))
    assert text.splitlines() == [
        "**笠松 1R（10:25 発走）** 地方の予想・当日の時点",
        "◎ 7 イチバン　○ 4 ニバン　▲ 8 サンバン",
        "実際に買う:",
        "単勝 ◎7 イチバン（期待値 1.05）100円",
        "複勝 3 ヨンバン（期待値 1.30）100円",
    ]


def test_前日の時点は買い目を出さず_その旨を書く() -> None:
    message = LocalRaceMessage()
    text = message.describe(message.card(_forecast("前日"), RACE, {}))
    assert "前日の時点（馬体重が届く前なのでオッズだけ）" in text.splitlines()[0]
    assert "買い目: なし（馬体重が届く前の前日の時点では買わない）" in text
    assert "100円" not in text


def test_レース一覧に無ければ_predict_の見出しを使う() -> None:
    message = LocalRaceMessage()
    card = message.card(_forecast("当日"), None, {})
    assert message.describe(card).startswith(f"**{RID}（2026-11-05）の予測: 当日の時点** 地方の予想・当日の時点")


def test_組み立てると_文と_保存した表の画像の添付(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    store.path(RID).parent.mkdir(parents=True)
    store.path(RID).write_text(json.dumps(_forecast("当日"), ensure_ascii=False), encoding="utf-8")
    notice = LocalRaceMessage(store=store, schedule=_Schedule(), frames=_Frames()).build(RID)
    assert notice.text.startswith("**笠松 1R（10:25 発走）** 地方の予想・当日の時点")
    assert notice.attachment == store.image_path(RID)
    assert notice.attachment.stat().st_size > 0
