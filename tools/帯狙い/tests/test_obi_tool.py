"""道具「帯狙い」の部品のテスト。架空の値だけを使い、実DB と学習済みモデルは使わない。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from yosou.shared.feature import PredictionTiming

from 今週の予想 import forecast_columns as columns
from 帯狙い.forecast_horses import ForecastHorses
from 帯狙い.obi_day_picker import DEFAULT_LINE, ObiDayPicker, RaceChance
from 帯狙い.obi_plans import DEFAULT_PLAN, PLAN_LABELS, plan_named
from 帯狙い.obi_store import ObiStore
from 帯狙い.obi_tables import ObiTables


def _forecast(win: bool = True, shift: float = 0.0) -> dict:
    horses = [{columns.HORSE_NO: number, columns.PROBABILITY: 0.6 - number * 0.05 + shift,
               columns.WIN_PROBABILITY: (0.3 - number * 0.02) if win else None} for number in range(1, 9)]
    return {"rid": "2026101805040211", "horses": horses}


def test_予想の結果から馬番と確率を取り出し1着の確率を合計1に直す() -> None:
    horses = ForecastHorses().of(_forecast())
    assert horses.horse_numbers.tolist() == list(range(1, 9))
    assert horses.win.sum() == pytest.approx(1.0)
    assert horses.by_win(1) == [1] and horses.by_top3(1) == [1]
    assert horses.usual_top3 is None


def test_1着の確率が無い時点は3着以内の確率で代わりにする() -> None:
    horses = ForecastHorses().of(_forecast(win=False))
    assert horses.win.sum() == pytest.approx(1.0)
    assert horses.by_win(3) == horses.by_top3(3)


def test_今の予想の結果を渡すとその3着以内の確率を馬番でそろえて入れる() -> None:
    horses = ForecastHorses().of(_forecast(), _forecast(shift=0.1))
    assert horses.usual_top3 is not None
    assert horses.usual_top3.tolist() == pytest.approx([0.6 - number * 0.05 + 0.1 for number in range(1, 9)])
    short = _forecast(shift=0.1)
    short["horses"] = short["horses"][:-1]  # 1頭足りない
    assert ForecastHorses().of(_forecast(), short).usual_top3 is None


def test_買い方は一律甲乙丙で既定は一律() -> None:
    assert list(PLAN_LABELS) == ["一律", "甲", "乙", "丙"]
    assert DEFAULT_PLAN == "一律"
    assert plan_named("一律").name == "一律 1,000倍以上（3連単・1点100円・100点）"
    assert plan_named("一律", 500).name == "一律 1,000倍以上（3連単・1点500円・20点）"
    assert plan_named("甲").ordered and plan_named("乙").ordered and not plan_named("丙").ordered
    with pytest.raises(ValueError):
        plan_named("丁")


def test_線以上のレースを全部選ぶ() -> None:
    ranked = [RaceChance("r1", PredictionTiming.RACE_DAY, 0.52), RaceChance("r2", PredictionTiming.RACE_DAY, DEFAULT_LINE),
              RaceChance("r3", PredictionTiming.RACE_DAY, 0.39)]
    assert [chance.race_id for chance in ObiDayPicker.above(ranked, DEFAULT_LINE)] == ["r1", "r2"]
    assert ObiDayPicker.above(ranked, 0.6) == []


def test_結果を開催日ごとに書いて読み戻し表にできる(tmp_path: Path) -> None:
    pick = {"rid": "r", "title": "架空のレース", "timing": "当日", "probability": 0.48,
            "horses": [{"馬番": 1, "馬名": "架空の馬", "印": "◎", "人気": 9, "単勝オッズ": 30.0, "3着以内の確率": 0.3, "1着の確率": 0.1,
                        "今の予想の3着以内の確率": 0.2}],
            "tickets": [{"組": "1-2-3", "掛け金": 100, "オッズ": 1500.0, "払戻の見込み": 150000}], "total_yen": 100, "note": "架空"}
    result = {"day": "2026-10-18", "plan": "一律 1,000倍以上（3連単・1点100円・100点）", "line": 0.4,
              "ranking": [{"rid": "r", "title": "架空のレース", "timing": "当日", "probability": 0.48, "chosen": True},
                          {"rid": "s", "title": "架空のレース2", "timing": "当日", "probability": 0.21, "chosen": False}],
              "picks": [pick, {**pick, "rid": "t", "tickets": [], "total_yen": 0}]}
    store = ObiStore(tmp_path)
    store.save(date(2026, 10, 18), result)
    assert store.load(date(2026, 10, 18)) == result
    assert store.load(date(2026, 10, 19)) is None
    tables = ObiTables().tables(result)
    assert [len(table.rows) for table in tables] == [2, 1, 1, 1, 0]
    assert tables[0].rows[0][-1] == "買う" and tables[0].rows[1][-1] == ""
