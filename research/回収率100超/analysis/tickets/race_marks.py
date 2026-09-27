"""レースごとに印（◎○▲△☆注）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 印の列の名前。△ は2頭まで付けるので2列。
MARKS: tuple[str, ...] = ("◎", "○", "▲", "△1", "△2", "☆", "注")
#: ☆ を付ける、複勝の期待値の下限。
STAR_FROM = 1.20
#: 人気馬の範囲（頭数 13 以下は 3番人気まで、14 以上は 5番人気まで）。それより下が穴馬。
_SMALL_FIELD_MAX, _SMALL_FIELD_FAVORITES, _LARGE_FIELD_FAVORITES = 13, 3, 5


class RaceMarks:
    """設計書「買うレースと買い目を決める」の 07 の 5 の決め方で印を付ける。

    - ◎○▲△: 3着以内の確率の 1〜5位（△ は 4・5位）。
    - ☆: ◎○▲ 以外の穴馬のうち、複勝の期待値が1位の馬。期待値 1.20 以上のときだけ。
    - 注: 印の無い馬のうち、「市場より来る」と見る度合い（ロジットの差）が最も大きい馬。
    危険な人気馬（消）は、この研究に人気馬の予想が無いので付けない。

    入力の列: rid・horse_no・p_placed（3着以内の確率）・market_placed（単勝から見た3着以内の確率）・
    popularity・field・place_ev（複勝の期待値）。出力は rid と印ごとの馬番（無ければ欠損）。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        table = runners.sort_values(["rid", "p_placed"], ascending=[True, False]).copy()
        table["rank"] = table.groupby("rid").cumcount() + 1
        marks = table.pivot(index="rid", columns="rank", values="horse_no").reindex(columns=range(1, 6))
        marks.columns = list(MARKS[:5])
        marks["☆"] = self._star(table)
        marks["注"] = self._note(table, marks["☆"])
        return marks.reset_index()

    def _star(self, table: pd.DataFrame) -> pd.Series:
        favorites = np.where(table["field"] <= _SMALL_FIELD_MAX, _SMALL_FIELD_FAVORITES,
                             _LARGE_FIELD_FAVORITES)
        pool = table[(table["popularity"] > favorites) & (table["rank"] > 3)
                     & (table["place_ev"] >= STAR_FROM)]
        best = pool.sort_values("place_ev", ascending=False).drop_duplicates("rid")
        return best.set_index("rid")["horse_no"]

    def _note(self, table: pd.DataFrame, star: pd.Series) -> pd.Series:
        unmarked = table[(table["rank"] > 5) & (table["horse_no"] != table["rid"].map(star))]
        uplift = self._logit(unmarked["p_placed"]) - self._logit(unmarked["market_placed"])
        best = unmarked.assign(uplift=uplift).sort_values("uplift", ascending=False).drop_duplicates("rid")
        return best.set_index("rid")["horse_no"]

    def _logit(self, probability: pd.Series) -> pd.Series:
        p = probability.clip(1e-6, 1 - 1e-6)
        return np.log(p / (1 - p))
