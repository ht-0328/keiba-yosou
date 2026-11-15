"""印の買い目の買い方の候補: どの買い方の点を、どの条件で、1点いくらで買うか。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby
from typing import Any

import pandas as pd

from 今週の予想.mark_return import MarkReturn

#: 買い方の出し方。点ごと: 条件に合う点を1点 100円で買う。レースごと: 中央の印の買い目と同じく、レースの点を どれが当たっても払った額より多く戻るように
#: 1レース 5,000円を配り（``MarkReturn``）、見込みの回収率（割合で重みを付けた期待値の和）が線以上のレースだけ買う。
PER_POINT, PER_RACE = "点ごと", "レースごと"
#: 選んだ点の表の列。``stake`` は1点の購入額（円）、``returned`` は当たったときに戻る額（外れは 0）。
CHOSEN_COLUMNS: tuple[str, ...] = ("race_id", "year", "race_date", "rule", "odds", "P", "ev", "stake", "returned")
_YEN_PER_POINT = 100
_RACE_DAY = "当日"


@dataclass(frozen=True)
class MarkPlan:
    """``rules`` の買い方の点を、``mode`` の出し方で買う。

    - ``ev_min``: 点ごとの期待値の線（点ごとのとき。None なら全部の点）。
    - ``line``: 見込みの回収率の線（レースごとのとき）。
    - ``min_heads``: 出走頭数の線。``top_value``: ◎ の単勝の期待値が 1.00 以上のレースだけにするか。
    トリガミ・オッズ無しで外した点（``dropped``）は、中央の印の買い目と同じく買わない（裏の点には付かない）。"""

    label: str
    rules: tuple[str, ...]
    mode: str = PER_POINT
    ev_min: float | None = None
    line: float = 1.0
    min_heads: int = 5
    top_value: bool = False

    def choose(self, table: pd.DataFrame) -> pd.DataFrame:
        rows = table[table["rule"].isin(self.rules) & ~table["dropped"].astype(bool) & (table["field_size"] >= self.min_heads)]
        rows = rows[rows["odds"].notna() & (rows["odds"] > 0)]
        if self.top_value:
            rows = rows[rows["top_band"] == "1.00 以上"]
        if self.mode == PER_POINT:
            if self.ev_min is not None:
                rows = rows[rows["ev"] >= self.ev_min]
            out = rows.assign(stake=_YEN_PER_POINT)
            out["returned"] = out["payout"].fillna(0.0)
            return out[list(CHOSEN_COLUMNS)].reset_index(drop=True)
        return self._per_race(rows)

    def _per_race(self, rows: pd.DataFrame) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        columns = ["race_id", "year", "race_date", "rule", "odds", "ev", "payout", "P"]
        ordered = rows.sort_values("race_id", kind="stable")[columns].to_dict("records")
        for race_id, group in groupby(ordered, key=lambda row: row["race_id"]):
            tickets = [{**row, "label": "", "value": float(row["ev"]), "dropped": False} for row in group]
            found = MarkReturn.of({"timing": _RACE_DAY, "tickets": tickets}, labels=self.rules)
            if found is None or found.expected is None or found.expected < self.line:
                continue
            for staked in found.stakes.values():
                for ticket, _, yen in staked:
                    records.append({"race_id": race_id, "year": ticket["year"], "race_date": ticket["race_date"], "rule": ticket["rule"],
                                    "odds": ticket["odds"], "P": ticket["P"], "ev": ticket["value"], "stake": yen,
                                    "returned": float(ticket["payout"]) * yen / _YEN_PER_POINT})
        return pd.DataFrame.from_records(records, columns=list(CHOSEN_COLUMNS))
