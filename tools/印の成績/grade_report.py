"""期待度（中央と地方で式と線が違う）の等級（S・A・B・C）ごとに、◎ の単勝・複勝の成績を並べる表を作る。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from yosou.shared.race_grade import GRADES, TopRankScale

from 共通.perf import PERF_COLUMNS, percent
from 共通.render import Table

from 今週の予想.forecast_columns import MARK, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.race_grades import RANK_LABEL, RANK_MEANING

from 印の成績.perf_rows import perf_row_of
from 印の成績.popularity_baseline import PopularityBaseline

#: 全部の ◎ の行の名前。
ALL_LABEL = "◎ 全体"
#: 同じ人気の馬全体と比べる率。
_BASELINE_RATES: tuple[str, ...] = ("勝率", "単勝回収率", "複勝率", "複勝回収率")


class RankScale(Protocol):
    """◎ の点数と等級の決め方（中央の ``TopRankScale``・地方の ``LocalExpectationScale``）。"""

    @staticmethod
    def score(win_probability: float | None, win_value: float | None) -> float | None: ...

    def grade(self, win_probability: float | None, win_value: float | None) -> str | None: ...

    @staticmethod
    def legend() -> str: ...


class GradeReport:
    """印を付けた表（``BacktestMarker.mark``）から、等級ごとの ◎ の成績の表（表13）を作る。

    等級は、◎ の1着になる確率と単勝の期待値（``win_probability``・``win_value``）から ``scale`` が決める。既定は中央の期待度
    （``TopRankScale``。◎ の単勝の期待値 0.90 未満は見送りの行に、それ以外は 1着の確率 ＋ 1.25 ×（期待値 − 1）を S 0.28・A 0.14・B 0.02 の線で）で、地方の予測は
    ``--scene 地方`` で期待度（``LocalExpectationScale``。期待値の重みが 3 で、線は S 0.45・A 0.15・B −0.10）にする。
    ``label``・``meaning`` は表の見出しと注に書く名前と意味。1着の予想が無ければ（◎ の期待値が無い）どの等級にも入らない。
    等級ごとに、レース数と割合、成績7つ、同じ人気の馬全体（``PopularityBaseline``）の勝率・単勝回収率・複勝率・複勝回収率を並べる。
    等級が高いほど勝率・複勝率・単勝回収率・複勝回収率が上がっていれば、等級はそのまま「◎ の単勝・複勝のべた買いの目安」として読める
    （設計書「買うレースと買い目を決める」の 03 の 5 と 11）。配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。
    """

    def __init__(self, scale: RankScale | None = None, label: str = RANK_LABEL, meaning: str = RANK_MEANING) -> None:
        self._scale = scale or TopRankScale()
        self._label = label
        self._meaning = meaning

    def table(self, marked: pd.DataFrame) -> Table:
        tops = marked[marked[MARK] == TOP_MARK]
        if WIN_PROBABILITY in tops.columns and WIN_VALUE in tops.columns:
            ranks = pd.Series([self._scale.grade(_number(probability), _number(value))
                               for probability, value in zip(tops[WIN_PROBABILITY], tops[WIN_VALUE], strict=True)], index=tops.index, dtype=object)
        else:
            ranks = pd.Series(None, index=tops.index, dtype=object)
        baseline = PopularityBaseline(marked)
        headers = [self._label, "レース数", "レースの割合", *PERF_COLUMNS[1:], *(f"同じ人気の馬全体の{name}" for name in _BASELINE_RATES)]
        extra = [grade for grade in ranks.dropna().unique() if grade not in GRADES]   # 中央の見送り
        rows = [self._row(grade, tops[ranks == grade], len(tops), baseline) for grade in (*GRADES, *extra)]
        rows.append(self._row(ALL_LABEL, tops, len(tops), baseline))
        return Table(headers, rows, title=f"13. {self._label}ごとの ◎ の単勝・複勝の成績",
                     note=f"{self._label}は{self._meaning}（{self._scale.legend()}。予想の表示と同じ決め方）。"
                          f"{self._label}が高いほど勝率・複勝率・単勝回収率・複勝回収率が上がっていれば、{self._label}は ◎ の単勝・複勝のべた買いの目安として読める。"
                          "「同じ人気の馬全体」は、その等級の ◎ と同じ人気の馬全体の成績を、◎ の人気の内訳で重み付けして平均したもの。"
                          "回収率は確定オッズの払戻で数えた。配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。")

    @staticmethod
    def _row(label: str, chosen: pd.DataFrame, total: int, baseline: PopularityBaseline) -> list[str]:
        if chosen.empty:
            return [label, "0", percent(0.0), "0-0-0-0", *["—"] * (len(PERF_COLUMNS) - 2 + len(_BASELINE_RATES))]
        rates = baseline.rates(chosen)
        return [label, f"{len(chosen):,}", percent(len(chosen) / total), *perf_row_of(chosen).cells()[1:],
                *(percent(rates[name]) for name in _BASELINE_RATES)]


def _number(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)
