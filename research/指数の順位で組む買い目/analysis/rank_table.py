"""予測と結果から、レースの中の順位の表を作る。"""

from __future__ import annotations

import pandas as pd

#: 順位の列。3着以内の確率の順（主）と 1着の確率の順（比べる）。
RANK_TOP3, RANK_WIN = "rank_top3", "rank_win"
#: 順位の決め方の名前 → 列。
RANKINGS: dict[str, str] = {"3着以内の確率の順": RANK_TOP3, "1着の確率の順": RANK_WIN}
#: そのレースで走った頭数（順位の表の行の数）。
FIELD = "field"
#: 順位の表の列。
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "horse_no", RANK_TOP3, RANK_WIN, FIELD, "finish", "popularity")


class RankTable:
    """全頭の予想（3着以内の確率）・1着の予想（1着の確率）のテスト期間の行と、レースの結果（走った馬だけ）から、
    レースの中の順位を付けた表（1行 = 1頭）を作る。

    順位は走った馬の中で確率の高い順（同じ確率は馬番の小さい順）。出走取消・除外の馬は結果に無いので順位に入らない
    （道具「印の成績」が印を付けるときと同じ）。1着の確率の無い馬は 1着の順で最下位側。
    """

    def build(self, top3: pd.DataFrame, win: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
        wins = win[["race_id", "horse_id", "probability"]].rename(columns={"probability": "win_probability"})
        table = (top3[["race_id", "race_date", "horse_id", "probability"]]
                 .merge(wins, on=["race_id", "horse_id"], how="left")
                 .merge(results[["race_id", "horse_id", "horse_no", "finish", "popularity"]], on=["race_id", "horse_id"], how="inner"))
        table["horse_no"] = table["horse_no"].astype(int)
        table[RANK_TOP3] = self._rank(table, "probability")
        table[RANK_WIN] = self._rank(table, "win_probability")
        table[FIELD] = table.groupby("race_id")["horse_no"].transform("size").astype(int)
        return table[list(COLUMNS)].sort_values(["race_id", RANK_TOP3]).reset_index(drop=True)

    @staticmethod
    def _rank(table: pd.DataFrame, column: str) -> pd.Series:
        """``column`` の高い順の順位（1 から）。欠損値は最後、同じ値は馬番の小さい順。"""
        ordered = table.sort_values(["race_id", column, "horse_no"], ascending=[True, False, True], na_position="last", kind="stable")
        ranks = ordered.groupby("race_id").cumcount() + 1
        return ranks.reindex(table.index).astype(int)
