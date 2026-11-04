"""騎手の場内順位: その競馬場で、前の年に何勝したかの順位（リーディング）。地方は騎手の偏りが大きいので、その場の上位かどうかを見る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 付ける列の名前。
JOCKEY_VENUE_RANK = "jockey_venue_rank"
JOCKEY_VENUE_WINS = "jockey_venue_wins"


@dataclass(frozen=True)
class JockeyVenueRank:
    """出走の表（事実表の行）から、競馬場 × 年 × 騎手の勝利数を数え、前の年の順位を各出走に付ける。

    前の年の値を使うのは、その出走の時点で分かっている情報にするため（同じ年の成績はレースの結果を含む）。
    前の年にその場で勝っていない騎手は順位が欠損値になる（圏外として扱う）。
    """

    def attach(self, runners: pd.DataFrame) -> pd.DataFrame:
        """``runners`` に ``jockey_venue_rank``（前の年の場内順位。1 が最上位）と ``jockey_venue_wins`` を足して返す。"""
        wins = self._yearly_wins(runners)
        wins["year"] = wins["year"] + 1          # 翌年の出走に「前の年の順位」として付ける
        return runners.merge(wins, on=["year", "venue_code", "jockey_code"], how="left")

    def _yearly_wins(self, runners: pd.DataFrame) -> pd.DataFrame:
        won = runners[runners["finish"] == 1]
        wins = won.groupby(["year", "venue_code", "jockey_code"]).size().rename(JOCKEY_VENUE_WINS).reset_index()
        wins[JOCKEY_VENUE_RANK] = wins.groupby(["year", "venue_code"])[JOCKEY_VENUE_WINS].rank(method="min", ascending=False)
        return wins
