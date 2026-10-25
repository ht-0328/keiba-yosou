"""的中率の等級（S・A・B・C）ごとに、◎ の成績を並べる表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.race_grade import GRADES, GradeScale

from 共通.perf import PERF_COLUMNS, percent
from 共通.render import Table

from 今週の予想.forecast_columns import MARK, PROBABILITY
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.race_grades import HIT_MEANING

from 印の成績.perf_rows import perf_row_of
from 印の成績.popularity_baseline import PopularityBaseline

#: 全部の ◎ の行の名前。
ALL_LABEL = "◎ 全体"
#: 同じ人気の馬全体と比べる率。
_BASELINE_RATES: tuple[str, ...] = ("複勝率", "複勝回収率")


class GradeReport:
    """印を付けた表（``BacktestMarker.mark``）から、的中率の等級ごとの ◎ の成績の表（表13）を作る。

    的中率は今週の予想と同じく ◎ の3着以内の確率（``probability``）で、等級は ``GradeScale`` の線（S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満）。
    等級ごとに、レース数と割合、成績7つ、同じ人気の馬全体（``PopularityBaseline``）の複勝率と複勝回収率を並べる。
    実際の複勝率が等級の線の中（S なら 75% 以上）に収まっていれば、確率はそのまま的中率として読める（設計書「買うレースと買い目を決める」の 03 の 5）。
    配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。
    """

    def table(self, marked: pd.DataFrame) -> Table:
        tops = marked[marked[MARK] == TOP_MARK]
        grades = tops[PROBABILITY].map(GradeScale().of)
        baseline = PopularityBaseline(marked)
        headers = ["的中率の等級", "レース数", "レースの割合", *PERF_COLUMNS[1:], *(f"同じ人気の馬全体の{name}" for name in _BASELINE_RATES)]
        rows = [self._row(grade, tops[grades == grade], len(tops), baseline) for grade in GRADES]
        rows.append(self._row(ALL_LABEL, tops, len(tops), baseline))
        return Table(headers, rows, title="13. 的中率の等級ごとの ◎ の成績",
                     note=f"的中率は{HIT_MEANING}（3着以内のモデル。今週の予想と同じ値）で、等級は {GradeScale.legend()}。"
                          "複勝率が等級の線の中に収まっていれば、確率はそのまま的中率として読める。"
                          "「同じ人気の馬全体」は、その等級の ◎ と同じ人気の馬全体の成績を、◎ の人気の内訳で重み付けして平均したもの。"
                          "回収率は確定オッズの払戻で数えた。配当率（荒れ具合の予想）は7つの区切りの予測が無いので、この表には出さない。")

    @staticmethod
    def _row(label: str, chosen: pd.DataFrame, total: int, baseline: PopularityBaseline) -> list[str]:
        if chosen.empty:
            return [label, "0", percent(0.0), "0-0-0-0", *["—"] * (len(PERF_COLUMNS) - 2 + len(_BASELINE_RATES))]
        rates = baseline.rates(chosen)
        return [label, f"{len(chosen):,}", percent(len(chosen) / total), *perf_row_of(chosen).cells()[1:],
                *(percent(rates[name]) for name in _BASELINE_RATES)]
