"""◎ランク（S・A・B・C）ごとに、◎ の単勝・複勝の成績を並べる表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.race_grade import GRADES, TopRankScale

from 共通.perf import PERF_COLUMNS, percent
from 共通.render import Table

from 今週の予想.forecast_columns import MARK, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.race_grades import RANK_MEANING

from 印の成績.perf_rows import perf_row_of
from 印の成績.popularity_baseline import PopularityBaseline

#: 全部の ◎ の行の名前。
ALL_LABEL = "◎ 全体"
#: 同じ人気の馬全体と比べる率。
_BASELINE_RATES: tuple[str, ...] = ("勝率", "単勝回収率", "複勝率", "複勝回収率")


class GradeReport:
    """印を付けた表（``BacktestMarker.mark``）から、◎ランクごとの ◎ の成績の表（表13）を作る。

    ◎ランクは今週の予想と同じく、◎ の1着になる確率 ＋ 単勝の期待値 − 1 の点数（``win_probability``・``win_value``）を ``TopRankScale`` の線
    （S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満）で分けたもの。1着の予想が無ければ（◎ の期待値が無い）どのランクにも入らない。
    ランクごとに、レース数と割合、成績7つ、同じ人気の馬全体（``PopularityBaseline``）の勝率・単勝回収率・複勝率・複勝回収率を並べる。
    ランクが高いほど勝率・複勝率・単勝回収率・複勝回収率が上がっていれば、ランクはそのまま「◎ の単勝・複勝のべた買いの目安」として読める
    （設計書「買うレースと買い目を決める」の 03 の 5）。配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。
    """

    def table(self, marked: pd.DataFrame) -> Table:
        tops = marked[marked[MARK] == TOP_MARK]
        scale = TopRankScale()
        if WIN_PROBABILITY in tops.columns and WIN_VALUE in tops.columns:
            scores = [TopRankScale.score(probability, value) for probability, value in zip(tops[WIN_PROBABILITY], tops[WIN_VALUE], strict=True)]
            ranks = pd.Series([scale.of(score) for score in scores], index=tops.index, dtype=object)
        else:
            ranks = pd.Series(None, index=tops.index, dtype=object)
        baseline = PopularityBaseline(marked)
        headers = ["◎ランク", "レース数", "レースの割合", *PERF_COLUMNS[1:], *(f"同じ人気の馬全体の{name}" for name in _BASELINE_RATES)]
        rows = [self._row(grade, tops[ranks == grade], len(tops), baseline) for grade in GRADES]
        rows.append(self._row(ALL_LABEL, tops, len(tops), baseline))
        return Table(headers, rows, title="13. ◎ランクごとの ◎ の単勝・複勝の成績",
                     note=f"◎ランクは{RANK_MEANING}（{TopRankScale.legend()}。今週の予想と同じ決め方）。"
                          "ランクが高いほど勝率・複勝率・単勝回収率・複勝回収率が上がっていれば、ランクは ◎ の単勝・複勝のべた買いの目安として読める。"
                          "「同じ人気の馬全体」は、そのランクの ◎ と同じ人気の馬全体の成績を、◎ の人気の内訳で重み付けして平均したもの。"
                          "回収率は確定オッズの払戻で数えた。配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。")

    @staticmethod
    def _row(label: str, chosen: pd.DataFrame, total: int, baseline: PopularityBaseline) -> list[str]:
        if chosen.empty:
            return [label, "0", percent(0.0), "0-0-0-0", *["—"] * (len(PERF_COLUMNS) - 2 + len(_BASELINE_RATES))]
        rates = baseline.rates(chosen)
        return [label, f"{len(chosen):,}", percent(len(chosen) / total), *perf_row_of(chosen).cells()[1:],
                *(percent(rates[name]) for name in _BASELINE_RATES)]
