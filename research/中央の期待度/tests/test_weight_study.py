"""中央の期待度の重みの研究（重みの候補・期間 × 等級の表・選び方）を、架空の ◎ の行で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from 中央の期待度.analysis.grade_period_table import GradePeriodTable  # noqa: E402
from 中央の期待度.analysis.weight_candidates import CANDIDATES, WEIGHTS, weighted  # noqa: E402
from 中央の期待度.analysis.weight_study import CURRENT_KEY, CandidateResult, WeightStudy  # noqa: E402


def _graded(grade_rows: dict[str, list[tuple[int, int, int]]]) -> pd.DataFrame:
    """等級 → [(着順, 単勝の払戻, 複勝の払戻), …] から ◎ の行を作る。"""
    rows = [{"grade": grade, "finish": finish, "win_payout": win, "place_payout": place, "year": 2025}
            for grade, items in grade_rows.items() for finish, win, place in items]
    return pd.DataFrame(rows)


def test_重みの候補は1が今の式で_確率と重みつきの期待値を足す() -> None:
    assert WEIGHTS[0] == 1.0 and [candidate.key for candidate in CANDIDATES][:2] == ["重み 1", "重み 1.5"]
    tops = pd.DataFrame({"win_probability": [0.30, 0.10], "win_value": [1.20, 0.90]})
    assert list(weighted(1.0).score(tops)) == pytest.approx([0.50, 0.00])
    assert list(weighted(3.0).score(tops)) == pytest.approx([0.90, -0.20])
    assert weighted(2.5).formula == "1着の確率 ＋ 2.5 ×（単勝の期待値 − 1）"


def test_等級の順に上がったかは4つの率ごとに真に上がったときだけ() -> None:
    graded = _graded({"S": [(1, 300, 150), (2, 0, 120)], "A": [(1, 250, 130), (4, 0, 0)],
                      "B": [(1, 200, 110), (5, 0, 0), (6, 0, 0)], "C": [(1, 150, 100), (7, 0, 0), (8, 0, 0), (9, 0, 0)]})
    rates = GradePeriodTable.rates(graded)
    assert rates["S"]["勝率"] == 0.5 and rates["S"]["単勝回収率"] == 1.5 and rates["C"]["複勝率"] == 0.25
    assert GradePeriodTable().monotone(graded) == {"勝率": False, "複勝率": True, "単勝回収率": True, "複勝回収率": True}   # 勝率は S と A が同じ
    assert GradePeriodTable().count(graded, [2025]) == 3


def test_等級が欠けた期間は順に上がったと数えない() -> None:
    graded = _graded({"S": [(1, 300, 150)], "A": [(1, 200, 120)], "B": [(4, 0, 0)]})
    assert not any(GradePeriodTable().monotone(graded).values())
    assert GradePeriodTable().rows(graded, "2025年")[3][2:] == ["0", "0.0%", "—", "—", "—", "—"]


def _result(key: str, decide_all: bool, decide_years: int) -> CandidateResult:
    flags = {rate: decide_all for rate in ("勝率", "複勝率", "単勝回収率", "複勝回収率")}
    return CandidateResult(key, key, {}, flags, decide_years, flags, 0)


def test_選び方は決める期間で全部順に上がる候補のうち年ごとの数が多いもの_同じなら重みの小さいもの() -> None:
    results = [_result("重み 1", False, 8), _result("重み 2", True, 6), _result("重み 3", True, 7), _result("重み 4", True, 7),
               _result(CURRENT_KEY, True, 8)]
    assert WeightStudy.choose(results).key == "重み 3"
    assert WeightStudy.choose([_result("重み 1", False, 8), _result(CURRENT_KEY, True, 8)]) is None


def test_決める年で線を決めて残りの年で確かめる表を書く(tmp_path: Path) -> None:
    rows = []
    for year in (2023, 2024, 2025):
        for i in range(40):
            probability = 0.05 + i * 0.01
            value = 0.8 + i * 0.01
            win = i % 3 == 0
            rows.append({"year": year, "win_probability": probability, "win_value": value, "finish": 1 if win else 5,
                         "win_payout": int(value / probability * 100) if win else 0, "place_payout": 150 if win else 0})
    study = WeightStudy(pd.DataFrame(rows), [2023, 2024])
    results = study.results()
    assert [result.key for result in results] == [*(candidate.key for candidate in CANDIDATES), CURRENT_KEY]
    assert results[-1].lines["S"] == 0.28   # 本番の線
    path = study.write(tmp_path / "重みの候補-当日.md")
    text = path.read_text(encoding="utf-8")
    assert "0. まとめ（当日。線は 2023〜2024年の分位で決め、2025年で確かめる）" in text and "2023〜2024年（決める）" in text
