"""道具「帯狙い」の部品のテスト。架空の値だけを使い、実DB と学習済みモデルは使わない。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from 今週の予想 import forecast_columns as columns
from 帯狙い.forecast_horses import ForecastHorses
from 帯狙い.obi_plans import DEFAULT_PLAN, PLANS
from 帯狙い.obi_store import ObiStore
from 帯狙い.obi_tables import ObiTables


def _forecast(win: bool = True) -> dict:
    horses = [{columns.HORSE_NO: number, columns.PROBABILITY: 0.6 - number * 0.05,
               columns.WIN_PROBABILITY: (0.3 - number * 0.02) if win else None} for number in range(1, 9)]
    return {"rid": "2026101805040211", "horses": horses}


def test_予想の結果から馬番と確率を取り出し1着の確率を合計1に直す() -> None:
    horses = ForecastHorses().of(_forecast())
    assert horses.horse_numbers.tolist() == list(range(1, 9))
    assert horses.win.sum() == pytest.approx(1.0)
    assert horses.by_win(1) == [1] and horses.by_top3(1) == [1]


def test_1着の確率が無い時点は3着以内の確率で代わりにする() -> None:
    horses = ForecastHorses().of(_forecast(win=False))
    assert horses.win.sum() == pytest.approx(1.0)
    assert horses.by_win(3) == horses.by_top3(3)


def test_買い方は甲乙丙で既定は帯を狙う甲() -> None:
    assert set(PLANS) == {"甲", "乙", "丙"}
    assert DEFAULT_PLAN == "甲"
    assert PLANS["甲"].ordered and PLANS["乙"].ordered and not PLANS["丙"].ordered


def test_結果を開催日ごとに書いて読み戻し表にできる(tmp_path: Path) -> None:
    result = {"day": "2026-10-18", "plan": "乙 本線厚め（3連単）",
              "ranking": [{"rid": "r", "title": "架空のレース", "timing": "当日", "probability": 0.08}],
              "pick": {"rid": "r", "title": "架空のレース", "timing": "当日", "probability": 0.08,
                       "horses": [{"馬番": 1, "馬名": "架空の馬", "印": "◎", "人気": 9, "単勝オッズ": 30.0, "3着以内の確率": 0.3, "1着の確率": 0.1}],
                       "tickets": [{"組": "1-2-3", "掛け金": 300, "オッズ": 1500.0, "払戻の見込み": 450000}], "total_yen": 300, "note": "架空"}}
    store = ObiStore(tmp_path)
    store.save(date(2026, 10, 18), result)
    assert store.load(date(2026, 10, 18)) == result
    assert store.load(date(2026, 10, 19)) is None
    tables = ObiTables().tables(result)
    assert [len(table.rows) for table in tables] == [1, 1, 1]
