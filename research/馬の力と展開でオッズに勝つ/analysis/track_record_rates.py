"""騎手・調教師・父などの「今回より前の成績」を、日付の順に数える。"""

from __future__ import annotations

import pandas as pd

#: 件数が少ないときに全体の平均へ寄せる強さ（出走数で数える）。
_SHRINK = 100.0


class TrackRecordRates:
    """区分（騎手・調教師・父 など。複数の列の組でもよい）ごとに、開催日の前日までの勝率と3着内率を数える。

    同じ日のレースの結果は使わない（同じ日の前のレースも使わない。発表の時点で分からないことがあるため）。
    件数が少ない区分は、全体の平均に寄せる: (勝ち数 + 100 × 全体の勝率) ÷ (出走数 + 100)。
    例: 騎手A が前日までに 50戦5勝なら、全体の勝率 0.07 として (5 + 7) ÷ 150 = 0.08。
    """

    def build(self, facts: pd.DataFrame, keys: list[str], name: str) -> pd.DataFrame:
        runs = facts[facts["ran"]].assign(won=lambda t: (t["finish"] == 1).astype(float),
                                          placed=lambda t: (t["finish"] <= 3).astype(float))
        daily = runs.groupby([*keys, "race_date"], as_index=False).agg(
            runs=("won", "size"), wins=("won", "sum"), places=("placed", "sum")).sort_values("race_date")
        grouped = daily.groupby(keys, sort=False)
        for column in ("runs", "wins", "places"):
            daily[f"before_{column}"] = grouped[column].cumsum() - daily[column]
        overall_win = runs["won"].mean()
        overall_place = runs["placed"].mean()
        daily[f"{name}_勝率"] = (daily["before_wins"] + _SHRINK * overall_win) / (daily["before_runs"] + _SHRINK)
        daily[f"{name}_3着内率"] = (daily["before_places"] + _SHRINK * overall_place) / (daily["before_runs"] + _SHRINK)
        daily[f"{name}_出走数"] = daily["before_runs"]
        rates = daily[[*keys, "race_date", f"{name}_勝率", f"{name}_3着内率", f"{name}_出走数"]]
        return facts[["race_id", "horse_no", *keys, "race_date"]].merge(
            rates, on=[*keys, "race_date"], how="left").drop(columns=[*keys, "race_date"])
