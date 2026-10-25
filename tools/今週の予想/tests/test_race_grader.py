"""レースの ◎ランク・的中率・配当率と等級（RaceGrades・PayoutRate・RaceGrader）のテスト。値は架空。"""

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


def _horses(win_probability: float | None = 0.23, win_value: float | None = 1.05) -> list[dict]:
    horses = [{"mark": "○", "win_probability": 0.3, "horse_no": 1}, {"mark": "▲", "win_probability": 0.2, "horse_no": 2}]
    if win_probability is not None:
        horses.append({"mark": "◎", "win_probability": win_probability, "win_value": win_value, "probability": 0.5, "horse_no": 3})
    return horses


def test_配当率は4券種の中荒れ以上の確率の平均で_出せなければ無し(capsys) -> None:
    rate = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.4, 0.5, 0.6, 0.7]))
    assert rate.of(None, "R", PredictionTiming.RACE_DAY) == pytest.approx(0.55)
    failing = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=FileNotFoundError("学習済みモデルがありません")))
    assert failing.of(None, "R", PredictionTiming.THURSDAY) is None
    assert "配当率（荒れ具合の予想）を出せません" in capsys.readouterr().err


def test_二重丸ランクは1着の確率と期待値の点数で_配当率は同じ線で等級にする() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.8, 0.8, 0.7, 0.9]))
    grades = grader.grade(None, "R", PredictionTiming.RACE_DAY, _horses())
    assert grades.rank_score == pytest.approx(0.28) and grades.rank == "A" and grades.hit_rate == 0.23
    assert grades.payout_rate == pytest.approx(0.8) and grades.payout_grade == "S"
    assert tuple(grades.as_dict()) == GRADE_KEYS
    assert grades.text() == "◎ランク A（的中率 23%）・配当率 S（80%）"


def test_期待値が無い木曜はランクが無く_二重丸がいなければ的中率も無し() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=ValueError("オッズがそろっていない")))
    thursday = grader.grade(None, "R", PredictionTiming.THURSDAY, _horses(win_value=None))
    assert thursday.rank is None and thursday.rank_score is None and thursday.hit_rate == 0.23 and thursday.payout_grade is None
    assert thursday.text() == "◎ランク なし・配当率 なし"
    none = grader.grade(None, "R", PredictionTiming.DAY_BEFORE, _horses(win_probability=None))
    assert none == RaceGrades(None, None, None, None, None)
    assert none.lines() == ["- ◎ランク: なし。◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝の的中率と回収率が高い",
                            "- 的中率: なし。◎ の単勝が当たる確率（1着になる確率）",
                            "- 配当率: なし。配当が中荒れ以上になる確率（荒れ具合の予想の単勝・馬連・3連複・3連単の平均）"]


def test_予想の結果の辞書から戻せて前の版の結果は全部無し() -> None:
    forecast = {"rid": "R", "rank_score": 0.4, "rank": "S", "hit_rate": 0.31, "payout_rate": 0.3, "payout_grade": "B"}
    assert RaceGrades.from_dict(forecast) == RaceGrades(0.4, "S", 0.31, 0.3, "B")
    assert RaceGrades.from_dict({"rid": "R", "expectation": "高"}) == RaceGrades(None, None, None, None, None)
    assert RaceGrades.from_dict({"rid": "R"}).text_if_any() == "" and RaceGrades.from_dict(forecast).text_if_any() == "◎ランク S（的中率 31%）・配当率 B（30%）"
    assert RaceGrades(None, None, None, 0.3, "B").text_if_any() == "◎ランク なし・配当率 B（30%）"
    assert RaceGrades.from_dict(forecast).lines()[0] == "- ◎ランク: S（点数 0.40）。◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝の的中率と回収率が高い"
    assert RaceGrades.legend().startswith("◎ランクは◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数")
    assert RaceGrades.legend().endswith("等級は S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満")
