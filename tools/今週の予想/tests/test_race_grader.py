"""レースの的中率・配当率と等級（RaceGrades・PayoutRate・RaceGrader）のテスト。値は架空。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from yosou.shared.feature import PredictionTiming
from yosou.upset_level.workflow import UPSET_OR_MORE

from 今週の予想.payout_rate import PayoutRate
from 今週の予想.race_grader import RaceGrader
from 今週の予想.race_grades import GRADE_KEYS, RaceGrades


class _Workflow:
    """荒れ具合の予想の代わり。4券種の中荒れ以上の確率を返す（``fail`` なら予測できない）。"""

    def __init__(self, rates: list[float], fail: Exception | None = None) -> None:
        self._rates, self._fail = rates, fail

    def run(self, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        if self._fail is not None:
            raise self._fail
        return pd.DataFrame({"券種": ["単勝", "馬連", "3連複", "3連単"], UPSET_OR_MORE: self._rates})


def _horses(top_probability: float | None = 0.42) -> list[dict]:
    horses = [{"mark": "○", "probability": 0.6, "horse_no": 1}, {"mark": "▲", "probability": 0.5, "horse_no": 2}]
    if top_probability is not None:
        horses.append({"mark": "◎", "probability": top_probability, "horse_no": 3})
    return horses


def test_配当率は4券種の中荒れ以上の確率の平均で_出せなければ無し(capsys) -> None:
    rate = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.4, 0.5, 0.6, 0.7]))
    assert rate.of(None, "R", PredictionTiming.RACE_DAY) == pytest.approx(0.55)
    failing = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=FileNotFoundError("学習済みモデルがありません")))
    assert failing.of(None, "R", PredictionTiming.THURSDAY) is None
    assert "配当率（荒れ具合の予想）を出せません" in capsys.readouterr().err


def test_的中率は二重丸の3着以内の確率で_どちらも同じ線で等級にする() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.8, 0.8, 0.7, 0.9]))
    grades = grader.grade(None, "R", PredictionTiming.RACE_DAY, _horses())
    assert (grades.hit_rate, grades.hit_grade, grades.payout_grade) == (0.42, "B", "S") and grades.payout_rate == pytest.approx(0.8)
    assert tuple(grades.as_dict()) == GRADE_KEYS and grades.as_dict()["hit_grade"] == "B"
    assert grades.text() == "的中率 B（42%）・配当率 S（80%）"


def test_二重丸がいないか配当率が出せなければその側は無し() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=ValueError("オッズがそろっていない")))
    grades = grader.grade(None, "R", PredictionTiming.DAY_BEFORE, _horses(top_probability=None))
    assert grades == RaceGrades(None, None, None, None)
    assert grades.text() == "的中率 なし・配当率 なし"
    assert grades.lines() == ["- 的中率: なし。◎ が3着以内に来る確率",
                              "- 配当率: なし。配当が中荒れ以上になる確率（荒れ具合の予想の単勝・馬連・3連複・3連単の平均）"]


def test_予想の結果の辞書から戻せて前の版の結果は全部無し() -> None:
    forecast = {"rid": "R", "hit_rate": 0.76, "hit_grade": "S", "payout_rate": 0.3, "payout_grade": "B"}
    assert RaceGrades.from_dict(forecast) == RaceGrades(0.76, "S", 0.3, "B")
    assert RaceGrades.from_dict({"rid": "R", "expectation": "高"}) == RaceGrades(None, None, None, None)
    assert RaceGrades.from_dict({"rid": "R"}).text_if_any() == "" and RaceGrades.from_dict(forecast).text_if_any() == "的中率 S（76%）・配当率 B（30%）"
    assert RaceGrades(None, None, 0.3, "B").text_if_any() == "的中率 なし・配当率 B（30%）"
    assert RaceGrades.legend().startswith("的中率は◎ が3着以内に来る確率、配当率は配当が中荒れ以上になる確率")
    assert RaceGrades.legend().endswith("等級は S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満")
