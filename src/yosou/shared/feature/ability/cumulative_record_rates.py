"""騎手・調教師・父などの「今回より前の通算の成績」を、日付の順に数える。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import PLACE_PRIOR, RECORD_SUFFIXES, WIN_PRIOR

#: 件数が少ないときに全体の平均へ寄せる強さ（出走数で数える）。
_SHRINK = 100.0


class CumulativeRecordRates:
    """区分（騎手・調教師・父 など。複数の列の組でもよい）ごとに、開催日の前日までの勝率と3着内率と出走数を数える。

    同じ日のレースの結果は使わない（同じ日の前のレースも使わない。発表の時点で分からないことがあるため）。
    件数が少ない区分は、全体の値（``WIN_PRIOR``・``PLACE_PRIOR``）に寄せる:
    (勝ち数 + 100 × 全体の勝率) ÷ (出走数 + 100)。
    例: 騎手A が前日までに 50戦5勝なら、全体の勝率 0.07 として (5 + 7) ÷ 150 = 0.08。
    ``runs`` は出走した馬の行（``finish`` は数。まだ走っていない行は欠損値）。
    """

    def build(self, runs: pd.DataFrame, keys: tuple[str, ...], name: str) -> pd.DataFrame:
        """列は race_id・horse_id と ``<name>_勝率``・``<name>_3着内率``・``<name>_出走数``。区分の値が無い行は欠損値。"""
        scored = runs.assign(won=(runs["finish"] == 1).astype(float), placed=(runs["finish"] <= 3).astype(float))
        daily = scored.groupby([*keys, "race_date"], as_index=False).agg(
            runs=("won", "size"), wins=("won", "sum"), places=("placed", "sum")).sort_values("race_date")
        grouped = daily.groupby(list(keys), sort=False)
        before = {column: grouped[column].cumsum() - daily[column] for column in ("runs", "wins", "places")}
        win, place, _ = (f"{name}_{suffix}" for suffix in RECORD_SUFFIXES)
        daily[win] = (before["wins"] + _SHRINK * WIN_PRIOR) / (before["runs"] + _SHRINK)
        daily[place] = (before["places"] + _SHRINK * PLACE_PRIOR) / (before["runs"] + _SHRINK)
        daily[f"{name}_出走数"] = before["runs"]
        rates = daily[[*keys, "race_date", win, place, f"{name}_出走数"]]
        return runs[["race_id", "horse_id", *keys, "race_date"]].merge(
            rates, on=[*keys, "race_date"], how="left").drop(columns=[*keys, "race_date"])
