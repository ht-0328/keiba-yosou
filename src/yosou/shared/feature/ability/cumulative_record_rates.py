"""騎手・調教師・父などの「今回より前の通算の成績」を、日付の順に数える。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import PLACE_PRIOR, RECORD_SUFFIXES, WIN_PRIOR
from .material_cutoff import MaterialCutoff

#: 件数が少ないときに全体の平均へ寄せる強さ（出走数で数える）。
_SHRINK = 100.0
_COUNTS = ("runs", "wins", "places")


class CumulativeRecordRates:
    """区分（騎手・調教師・父 など。複数の列の組でもよい）ごとに、材料の締めの日までの勝率と3着内率と出走数を数える。

    締めの日は ``MaterialCutoff``（行に ``as_of_date`` があればその日まで、無ければ開催日の前日まで）。
    同じ日のレースの結果は使わない（同じ日の前のレースも使わない。発表の時点で分からないことがあるため）。
    件数が少ない区分は、全体の値（``WIN_PRIOR``・``PLACE_PRIOR``）に寄せる:
    (勝ち数 + 100 × 全体の勝率) ÷ (出走数 + 100)。
    例: 騎手A が前日までに 50戦5勝なら、全体の勝率 0.07 として (5 + 7) ÷ 150 = 0.08。
    ``runs`` は出走した馬の行（``finish`` は数。まだ走っていない行は欠損値）。
    """

    def __init__(self) -> None:
        self._cutoff = MaterialCutoff()

    def build(self, runs: pd.DataFrame, keys: tuple[str, ...], name: str) -> pd.DataFrame:
        """列は race_id・horse_id と ``<name>_勝率``・``<name>_3着内率``・``<name>_出走数``。区分の値が無い行は欠損値。"""
        key_list = list(keys)
        daily = self._daily(runs, key_list)
        # 鍵の列の型は daily と同じにする（merge_asof は by の型が違うと止まる）
        query = runs[key_list].reset_index(drop=True).assign(cutoff=self._cutoff.of(runs).to_numpy(), order=range(len(runs)))
        valid = query.dropna(subset=key_list).sort_values("cutoff", kind="stable")
        valid = valid.astype({key: daily[key].dtype for key in key_list})
        found = pd.merge_asof(valid, daily, left_on="cutoff", right_on="race_date", by=key_list, direction="backward")
        found = found.set_index("order").reindex(range(len(runs)))
        # 締めの日までに記録の無い区分は 0（全体の値に寄せた率と出走数 0 になる）
        before = {column: found[f"cum_{column}"].fillna(0.0).astype(float).to_numpy() for column in _COUNTS}
        has_key = query[key_list].notna().all(axis=1).to_numpy()
        win, place, count = (f"{name}_{suffix}" for suffix in RECORD_SUFFIXES)
        table = pd.DataFrame({
            "race_id": runs["race_id"].to_numpy(), "horse_id": runs["horse_id"].to_numpy(),
            win: (before["wins"] + _SHRINK * WIN_PRIOR) / (before["runs"] + _SHRINK),
            place: (before["places"] + _SHRINK * PLACE_PRIOR) / (before["runs"] + _SHRINK),
            count: before["runs"],
        })
        # 区分の値が無い行は欠損値。値はあるが締めの日までに記録が無い区分は、全体の値に寄せた値と出走数 0
        for column in (win, place, count):
            table[column] = table[column].where(has_key)
        return table

    def _daily(self, runs: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """区分・開催日ごとの、その日までの累積（出走・勝ち・3着内。その日を含む）。merge_asof のために開催日の順に並べる。"""
        scored = runs.assign(won=(runs["finish"] == 1).astype(float), placed=(runs["finish"] <= 3).astype(float),
                             race_date=pd.to_datetime(runs["race_date"]))
        daily = scored.groupby([*keys, "race_date"], as_index=False).agg(
            runs=("won", "size"), wins=("won", "sum"), places=("placed", "sum")).sort_values([*keys, "race_date"])
        grouped = daily.groupby(keys, sort=False)
        for column in _COUNTS:
            daily[f"cum_{column}"] = grouped[column].cumsum().astype(float)
        columns = [*keys, "race_date", *(f"cum_{column}" for column in _COUNTS)]
        return daily[columns].sort_values("race_date", kind="stable").reset_index(drop=True)
