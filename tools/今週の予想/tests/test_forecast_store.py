"""ForecastStore（予想の結果を書く・読む）と ForecastTable（表にする）のテスト。値は架空。"""

from __future__ import annotations

from pathlib import Path

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.forecast_table import ForecastTable


def sample_forecast(race_id: str = "2025041905010101") -> dict:
    horse = {"rank": 1, "mark": "◎", "mark_reason": "単勝の期待値がレース内1位", "horse_no": 3, "horse_name": "馬A",
             "horse_id": "2021100001", "probability": 0.42, "win_odds": 3.1, "popularity": 1.0, "market_top3": 0.4,
             "place_value": 1.05, "updown": 0.08, "win_probability": 0.35, "win_value": 1.085,
             "good": [{"category": "能力", "effect": 3.0, "logit": 0.2, "details": []}],
             "bad": [], "categories": [], "summary": "総合の文", "role": "勝ってほしい馬"}
    return {"rid": race_id, "title": "2025-04-19（土） 東京 1R", "header": {}, "model": "近走と適性から3着以内を予想",
            "timing": "前日", "timing_reason": "出馬表とオッズがある", "pool_free": False, "expectation": "高",
            "made_at": "2025-04-18T20:00:00", "horses": [horse]}


def test_開催日のフォルダに書いて読み戻せる(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    path = store.save(sample_forecast())
    assert path == tmp_path / "2025-04-19" / "2025041905010101.json"
    assert store.load("2025041905010101")["horses"][0]["horse_name"] == "馬A"
    assert store.saved_at("2025041905010101") == "2025-04-18T20:00:00"
    assert store.load("2025041905010102") is None


def test_表にすると良い点の分類が並ぶ() -> None:
    table = ForecastTable().table(sample_forecast())
    assert table.rows[0][:5] == [1, "◎", 3, "馬A", "42.0%"]
    assert table.rows[0][-2] == "能力"
    assert table.rows[0][9:11] == ["35.0%", "1.08"]  # 1着の確率と単勝の期待値（1.085 は丸めて 1.08）
    assert "前日" in table.note and "期待度: 高" in table.note
