"""比べる相手（今の印の買い目を全レースで買ったもの）を、道具「印の成績」の買い目の CSV から開催日ごとにまとめる。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 比べる相手の買い方（設計書「買うレースと買い目を決める」08 の 2 の形。券種 → 買い方の名前）。枠連は今の形が無い。
BASELINE_RULES: dict[str, str] = {
    "単勝": "単勝", "複勝": "複勝", "ワイド": "ワイド", "馬連": "馬連", "馬単": "馬単",
    "3連複": "3連複（◎−○▲☆−○▲△☆）", "3連単": "3連単（◎→○▲☆→○▲△☆）",
}
#: まとめた表の列。
COLUMNS: tuple[str, ...] = ("券種", "race_date", "points", "payout", "races", "hits")
_USE: tuple[str, ...] = ("レースID", "開催日", "買い方", "払戻（100円あたり）", "外した理由")


class BaselineTickets:
    """道具「印の成績」の買い目の CSV（1行 = 1点。2015年からの当日の予想）から、``BASELINE_RULES`` の買い方の、外した理由の無い買い目
    （トリガミとオッズ無しを除いたもの）を券種ごと・開催日ごとに、点数・払戻・買ったレース・当たったレースにまとめる（docs/01 の 6 の比べる相手）。

    CSV は大きい（1GB ほど）ので、必要な列だけ少しずつ読む。結果は ``比べる相手.parquet`` に書いて使い回す。
    """

    def summarize(self, csv_path: Path, chunk_rows: int = 2_000_000) -> pd.DataFrame:
        parts = []
        for chunk in pd.read_csv(csv_path, usecols=list(_USE), chunksize=chunk_rows, dtype={"レースID": str, "外した理由": str}):
            kept = chunk[chunk["買い方"].isin(BASELINE_RULES.values()) & chunk["外した理由"].isna()]
            if kept.empty:
                continue
            per_race = kept.groupby(["買い方", "開催日", "レースID"], sort=False)["払戻（100円あたり）"].agg(["size", "sum"])
            parts.append(per_race)
        if not parts:
            return pd.DataFrame(columns=list(COLUMNS))
        per_race = pd.concat(parts).groupby(level=[0, 1, 2]).sum()
        per_race["hit"] = (per_race["sum"] > 0).astype(float)
        per_day = per_race.groupby(level=[0, 1]).agg(points=("size", "sum"), payout=("sum", "sum"), races=("size", "size"), hits=("hit", "sum")).reset_index()
        labels = {rule: ticket for ticket, rule in BASELINE_RULES.items()}
        per_day["券種"] = per_day["買い方"].map(labels)
        per_day["race_date"] = pd.to_datetime(per_day["開催日"])
        return per_day[list(COLUMNS)].sort_values(["券種", "race_date"]).reset_index(drop=True)
