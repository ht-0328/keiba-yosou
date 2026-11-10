"""期待度の点数の候補（◎ の確率と期待値から1つの点数を作る式）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from 今週の予想.forecast_columns import PLACE_VALUE, PROBABILITY, WIN_PROBABILITY, WIN_VALUE


@dataclass(frozen=True)
class ScoreCandidate:
    """``key`` は短い名前、``formula`` は人が読む式、``compute`` は ◎ の行の表（列 ``win_probability``・``win_value``・``probability``・``place_value``）から点数を出す。"""

    key: str
    formula: str
    compute: Callable[[pd.DataFrame], pd.Series]

    def score(self, tops: pd.DataFrame) -> pd.Series:
        return self.compute(tops).astype(float)


def _p1(t: pd.DataFrame) -> pd.Series:
    return t[WIN_PROBABILITY].astype(float)


def _ev(t: pd.DataFrame) -> pd.Series:
    return t[WIN_VALUE].astype(float) - 1.0


def _p3(t: pd.DataFrame) -> pd.Series:
    return t[PROBABILITY].astype(float)


def _pv(t: pd.DataFrame) -> pd.Series:
    return t[PLACE_VALUE].astype(float) - 1.0


#: 候補（結果を見る前に決めた一覧）。中央の ◎ランクの式（1着の確率 ＋ 単勝の期待値 − 1）を A とし、確率と期待値の重みを変えたもの、片方だけ、
#: 3着以内の確率と複勝の期待値で作るもの、積を並べる。
CANDIDATES: tuple[ScoreCandidate, ...] = (
    ScoreCandidate("A", "1着の確率 ＋（単勝の期待値 − 1）", lambda t: _p1(t) + _ev(t)),
    ScoreCandidate("B", "1着の確率だけ", _p1),
    ScoreCandidate("C", "単勝の期待値 − 1 だけ", _ev),
    ScoreCandidate("D", "1着の確率 ＋ 2 ×（単勝の期待値 − 1）", lambda t: _p1(t) + 2 * _ev(t)),
    ScoreCandidate("E", "2 × 1着の確率 ＋（単勝の期待値 − 1）", lambda t: 2 * _p1(t) + _ev(t)),
    ScoreCandidate("F", "3着以内の確率 ＋（複勝の期待値 − 1）", lambda t: _p3(t) + _pv(t)),
    ScoreCandidate("G", "1着の確率 ＋（単勝の期待値 − 1）＋（複勝の期待値 − 1）", lambda t: _p1(t) + _ev(t) + _pv(t)),
    ScoreCandidate("H", "1着の確率 × 単勝の期待値", lambda t: _p1(t) * (_ev(t) + 1.0)),
    ScoreCandidate("I", "1着の確率 ＋ 3 ×（単勝の期待値 − 1）", lambda t: _p1(t) + 3 * _ev(t)),
    ScoreCandidate("J", "1着の確率 ＋ 0.5 ×（単勝の期待値 − 1）", lambda t: _p1(t) + 0.5 * _ev(t)),
)
