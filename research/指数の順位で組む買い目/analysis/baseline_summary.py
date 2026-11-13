"""比べる相手（今の印の買い目）を、道具「印の成績」の買い目の CSV からレースごとにまとめる。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 比べる相手の買い方（設計書「買うレースと買い目を決める」08 の 2 の形。買い方の名前 → 券種）。
#: 「馬単（設計書に無い）」は、道具「印の成績」の前の版が馬単の買い目に付けていた名前（同じ ◎→○▲☆ の形）。
BASELINE_RULES: dict[str, str] = {
    "単勝": "単勝", "複勝": "複勝", "ワイド": "ワイド", "馬連": "馬連", "馬単": "馬単", "馬単（設計書に無い）": "馬単",
    "3連複（◎−○▲☆−○▲△☆）": "3連複", "3連単（◎→○▲☆→○▲△☆）": "3連単",
}
#: まとめた表の列（この研究の精算の表と同じ並び。``formation`` に買い方の名前が入る）。
COLUMNS: tuple[str, ...] = ("formation", "ticket", "race_id", "race_date", "points", "payout", "hit")
_USE: tuple[str, ...] = ("レースID", "開催日", "買い方", "払戻（100円あたり）", "外した理由")


class BaselineSummary:
    """道具「印の成績」の買い目の CSV（1行 = 1点）から、``BASELINE_RULES`` の買い方の、外した理由の無い買い目
    （トリガミとオッズ無しを除いたもの）を、買い方ごと・レースごとの点数・払戻（1点 100円あたりの合計）・的中にまとめる。

    CSV は大きい（数百 MB〜1GB ほど）ので、必要な列だけ少しずつ読む。
    """

    def summarize(self, csv_path: Path, chunk_rows: int = 2_000_000) -> pd.DataFrame:
        parts = []
        for chunk in pd.read_csv(csv_path, usecols=list(_USE), chunksize=chunk_rows, dtype={"レースID": str, "外した理由": str}):
            kept = chunk[chunk["買い方"].isin(BASELINE_RULES) & chunk["外した理由"].isna()]
            if kept.empty:
                continue
            parts.append(kept.groupby(["買い方", "レースID", "開催日"], sort=False)["払戻（100円あたり）"].agg(["size", "sum"]))
        if not parts:
            return pd.DataFrame(columns=list(COLUMNS))
        per_race = pd.concat(parts).groupby(level=[0, 1, 2]).sum().reset_index()
        table = pd.DataFrame({
            "formation": per_race["買い方"].astype(str), "ticket": per_race["買い方"].map(BASELINE_RULES).astype(str),
            "race_id": per_race["レースID"].astype(str), "race_date": pd.to_datetime(per_race["開催日"]),
            "points": per_race["size"].astype(int), "payout": per_race["sum"].astype(float),
        })
        table["hit"] = table["payout"] > 0
        return table[list(COLUMNS)].sort_values(["formation", "race_date", "race_id"]).reset_index(drop=True)
