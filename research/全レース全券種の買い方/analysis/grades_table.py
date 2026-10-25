"""レースごとの ◎ランク・的中率・配当率とその等級、◎ のオッズの帯の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.race_grade import GradeScale, TopRankScale

from .upset_walk_forward import PAYOUT_RATE

#: 表の列。等級が無い（配当率を出せなかった・期待値が無い）レースは ``NO_GRADE``。
HIT_RATE, RANK_SCORE, RANK, PAYOUT_GRADE, CELL = "hit_rate", "rank_score", "rank", "payout_grade", "cell"
TOP_ODDS, ODDS_BAND = "top_odds", "odds_band"
NO_GRADE = "－"
#: ◎ の単勝オッズの帯。2倍以下のレースは、単勝で勝負する価値が無いので別の場面にする（docs/01 の 8。3回目から）。
LOW_ODDS_BAND, NORMAL_ODDS_BAND = "2倍以下", "2倍超"
LOW_ODDS_LINE = 2.0
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", HIT_RATE, RANK_SCORE, RANK, PAYOUT_RATE, PAYOUT_GRADE, TOP_ODDS, ODDS_BAND, CELL)


class GradesTable:
    """印を付けた表（``marked-2015から.parquet``。1行 = 1頭）と、区切りごとの配当率（``UpsetWalkForward.payout_rates``）から、
    レースごとの ◎ランク（◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。``TopRankScale``）・的中率（◎ の1着の確率）・配当率と、その等級（``GradeScale``。今週の予想と同じ線）、
    ◎ の単勝オッズの帯を作る（docs/01 の 2・8）。

    セル（``cell``）は「◎ランク × 配当率の等級」を ``S/A`` のように1つの文字列にしたもの。配当率の無いレースは ``S/－``。
    ``split_low_odds`` が真なら、◎ が 2倍以下のレースは配当率の等級の代わりに ``2倍以下`` を使う（``S/2倍以下``）。単勝で勝負しない場面を分けるため（3回目から）。
    """

    def __init__(self, split_low_odds: bool = True) -> None:
        self._scale = GradeScale()
        self._rank = TopRankScale()
        self._split_low_odds = split_low_odds

    def build(self, marked: pd.DataFrame, payout_rates: pd.DataFrame | None) -> pd.DataFrame:
        columns = ["race_id", "race_date", "fold", "win_probability", "win_value", "win_odds"]
        tops = marked[marked["mark"] == "◎"][columns].drop_duplicates("race_id")
        table = tops.rename(columns={"win_probability": HIT_RATE, "win_odds": TOP_ODDS}).reset_index(drop=True)
        table["race_id"] = table["race_id"].astype(str)
        table[RANK_SCORE] = [TopRankScale.score(probability, value) for probability, value in zip(table[HIT_RATE], table["win_value"], strict=True)]
        if payout_rates is not None and not payout_rates.empty:
            rates = payout_rates[["race_id", PAYOUT_RATE]].assign(race_id=lambda frame: frame["race_id"].astype(str)).drop_duplicates("race_id")
            table = table.merge(rates, on="race_id", how="left")
        else:
            table[PAYOUT_RATE] = float("nan")
        table[RANK] = table[RANK_SCORE].map(self._rank.of).fillna(NO_GRADE)
        table[PAYOUT_GRADE] = table[PAYOUT_RATE].map(self._scale.of).fillna(NO_GRADE)
        low = table[TOP_ODDS].astype(float) <= LOW_ODDS_LINE
        table[ODDS_BAND] = low.map({True: LOW_ODDS_BAND, False: NORMAL_ODDS_BAND})
        second = table[PAYOUT_GRADE].where(~(low & self._split_low_odds), LOW_ODDS_BAND)
        table[CELL] = table[RANK] + "/" + second
        return table[list(COLUMNS)]
