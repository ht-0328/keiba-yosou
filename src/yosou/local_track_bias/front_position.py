"""過去の全出走から、馬ごとの前らしさの見込み（直近3走の4コーナーの位置の平均）を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

#: 前らしさの見込みの列。``BiasCorrection`` が読む展開の予想④と同じ名前（0 が先頭、1 が最後方）。
FRONT_POSITION = "corner4_pred"
#: 平均する直近の走数。
RECENT_RUNS = 3
#: 作業用の列。
_POSITION, _MEAN = "_position", "_mean"


class FrontPosition:
    """``runs``（``BiasRunRepository`` の表。``race_id``・``race_date``・``horse_id``・``corner4``・``field_size``）から、馬ごとに
    「そのレースより前の直近 ``RECENT_RUNS`` 走（4コーナーの順位のある出走だけ）の位置の平均」を出す。

    位置 = （4コーナーの順位 − 1）÷（頭数 − 1）。0 が先頭、1 が最後方（``Positions`` の前らしさの元と同じ）。
    直近の走が無い馬（初出走・転入初戦）は欠損値。同じ馬の2走は、開催日と race_id の順で前のものだけを数える。
    中央の展開の予想④の代わりなので、展開の予想が無い地方でも「前に行きそうな馬か」を過去の走りから見込める。
    """

    def of(self, runs: pd.DataFrame) -> pd.DataFrame:
        """列は ``race_id``・``horse_id``・``corner4_pred``。行の並びと index は ``runs`` と同じ。"""
        rank = as_numbers(runs["corner4"])
        size = as_numbers(runs["field_size"])
        table = pd.DataFrame({
            "race_id": runs["race_id"].astype(str), "horse_id": runs["horse_id"].astype(str),
            "race_date": pd.to_datetime(runs["race_date"]), _POSITION: ((rank - 1) / (size - 1).where(size > 1)),
        }, index=runs.index)
        ordered = table.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        known = ordered[ordered[_POSITION].notna()]
        # 4コーナーの順位のある走だけで、その走までの直近 RECENT_RUNS 走の平均（自分を含む）
        means = known.groupby("horse_id", sort=False)[_POSITION].rolling(RECENT_RUNS, min_periods=1).mean()
        ordered[_MEAN] = means.reset_index(level=0, drop=True).reindex(ordered.index)
        # 直前の走までの平均 = 自分の1つ前の行（順位の無い走も含めて）の、そこまでの平均
        carried = ordered.groupby("horse_id", sort=False)[_MEAN].ffill()
        before = carried.groupby(ordered["horse_id"], sort=False).shift(1)
        return pd.DataFrame({
            "race_id": table["race_id"], "horse_id": table["horse_id"], FRONT_POSITION: before.reindex(table.index).astype("float64"),
        }, index=runs.index)
