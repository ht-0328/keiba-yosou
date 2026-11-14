"""レースの期待度・的中率・配当率と等級（RaceGrades・PayoutRate・RaceGrader）のテスト。値は架空。"""

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
    """荒れ具合の予想の代わり。4券種の荒れ具合の確率と中荒れ以上の確率を返す（``fail`` なら予測できない）。3連複は大荒れの確率がいちばん高い。"""

    def __init__(self, rates: list[float], fail: Exception | None = None) -> None:
        self._rates, self._fail = rates, fail

    def run(self, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        if self._fail is not None:
            raise self._fail
        return pd.DataFrame({"券種": ["単勝", "馬連", "3連複", "3連単"], UPSET_OR_MORE: self._rates,
                             "固い": [0.7, 0.2, 0.2, 0.1], "中荒れ": [0.1, 0.5, 0.3, 0.1],
                             "大荒れ": [0.1, 0.2, 0.4, 0.2], "超荒れ": [0.1, 0.1, 0.1, 0.6]})


def _horses(win_probability: float | None = 0.23, win_value: float | None = 1.05) -> list[dict]:
    horses = [{"mark": "○", "win_probability": 0.3, "horse_no": 1}, {"mark": "▲", "win_probability": 0.2, "horse_no": 2}]
    if win_probability is not None:
        horses.append({"mark": "◎", "win_probability": win_probability, "win_value": win_value, "probability": 0.5, "horse_no": 3})
    return horses


def test_配当率は4券種の中荒れ以上の確率の平均で3連複の荒れ具合も出し_出せなければ無し(capsys) -> None:
    rate = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.4, 0.5, 0.6, 0.7]))
    payout, trio = rate.of(None, "R", PredictionTiming.RACE_DAY)
    assert payout == pytest.approx(0.55) and trio == "大荒れ"
    failing = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=FileNotFoundError("学習済みモデルがありません")))
    assert failing.of(None, "R", PredictionTiming.THURSDAY) == (None, None)
    assert "配当率（荒れ具合の予想）を出せません" in capsys.readouterr().err


def test_期待度は1着の確率と重みつきの期待値の点数で_配当率は確率の線で等級にする() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.8, 0.8, 0.7, 0.9]))
    grades = grader.grade(None, "R", PredictionTiming.RACE_DAY, _horses())
    assert grades.rank_score == pytest.approx(0.23 + 1.25 * 0.05) and grades.rank == "S" and grades.hit_rate == 0.23   # 0.2925 は S（0.28 以上）
    assert grades.payout_rate == pytest.approx(0.8) and grades.payout_grade == "S" and grades.trio_upset == "大荒れ"
    assert tuple(grades.as_dict()) == GRADE_KEYS
    assert grades.text() == "期待度 S（点数 0.29）" and grades.badge() == "期待度 S"


def test_二重丸の期待値が線未満なら見送り() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([0.8, 0.8, 0.7, 0.9]))
    skipped = grader.grade(None, "R", PredictionTiming.RACE_DAY, _horses(win_probability=0.40, win_value=0.89))
    assert skipped.rank == "見送り" and skipped.skipped and skipped.rank_score == pytest.approx(0.40 - 1.25 * 0.11)
    assert skipped.text() == "期待度 見送り（◎ の単勝の期待値が 0.90 未満）" and skipped.badge() == "期待度 見送り"
    assert skipped.text_if_any() == skipped.text()
    edge = grader.grade(None, "R", PredictionTiming.RACE_DAY, _horses(win_probability=0.10, win_value=0.90))   # 線ちょうどは見送りでない
    assert edge.rank == "C" and not edge.skipped   # 0.10 − 0.125 = −0.025 は C（0.02 未満）


def test_期待値が無い木曜はランクが無く_二重丸がいなければ的中率も無し() -> None:
    grader = RaceGrader(Path("models"))
    grader._payout = PayoutRate(Path("models"), runner=lambda con: _Workflow([], fail=ValueError("オッズがそろっていない")))
    thursday = grader.grade(None, "R", PredictionTiming.THURSDAY, _horses(win_value=None))
    assert thursday.rank is None and thursday.rank_score is None and thursday.hit_rate == 0.23 and thursday.payout_grade is None
    assert thursday.text() == "期待度 なし（単勝オッズが出る前なので出さない）" and thursday.badge() == ""
    none = grader.grade(None, "R", PredictionTiming.DAY_BEFORE, _horses(win_probability=None))
    assert none == RaceGrades(None, None, None, None, None)
    assert none.lines() == ["- 期待度 なし（単勝オッズが出る前なので出さない）。◎ の単勝の期待値が 0.90 未満のレースは見送り（◎ の単勝が 100% を割る）。それ以外は S・A・B・C のどれも ◎ の単勝の回収率が 100% を超え、等級が高いほど ◎ の的中率が高い"]


def test_予想の結果の辞書から戻せて前の版の結果は全部無し() -> None:
    forecast = {"rid": "R", "rank_score": 0.4, "rank": "S", "hit_rate": 0.31, "payout_rate": 0.3, "payout_grade": "B", "trio_upset": "中荒れ"}
    assert RaceGrades.from_dict(forecast) == RaceGrades(0.4, "S", 0.31, 0.3, "B", "中荒れ")
    assert RaceGrades.from_dict({"rid": "R", "expectation": "高"}) == RaceGrades(None, None, None, None, None)
    assert RaceGrades.from_dict({"rid": "R"}).text_if_any() == "" and RaceGrades.from_dict(forecast).text_if_any() == "期待度 S（点数 0.40）"
    assert RaceGrades(None, None, None, 0.3, "B").text_if_any() == ""   # 配当率だけあっても、期待度が無ければ出さない
    assert RaceGrades.from_dict(forecast).lines() == ["- 期待度 S（点数 0.40）。◎ の単勝の期待値が 0.90 未満のレースは見送り（◎ の単勝が 100% を割る）。それ以外は S・A・B・C のどれも ◎ の単勝の回収率が 100% を超え、等級が高いほど ◎ の的中率が高い"]
    assert RaceGrades.legend().startswith("期待度は◎ の単勝の期待値が 0.90 未満のレースは見送り")
    assert RaceGrades.legend().endswith("S 0.28 以上・A 0.14 以上・B 0.02 以上・C 0.02 未満）") and "配当率" not in RaceGrades.legend()
