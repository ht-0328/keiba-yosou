"""1か月ぶんのレースの、券種ごとの全部の組の表（4つのもとと、当たったか）を作る。"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import HARVILLE, HIT, MARKET, ComboBlendFeatures, HorseStrength, PoolFolding, TrifectaSources, split_combo
from yosou.shared.repository import FinalOddsRepository, PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN

#: 組に写すレースの列。``top`` は ◎ の馬番。
RACE_COLUMNS: tuple[str, ...] = ("race_date", "expectation", "fold", "top")
#: 当たった組の 100円あたりの払戻の列。
PAYOUT = "payout"


class ComboMonthFrames:
    """印を付けた表（``BacktestMarking.mark``）の1か月ぶんと、その月の確定オッズの板・払戻の明細から、券種ごとに1行 = 1組の表を作る。

    列は ``ComboBlendFeatures.build`` の列（4つのもと）と、``hit``（当たったか）・``payout``（100円あたりの払戻。外れは 0）・
    ``RACE_COLUMNS``。組の確率の作り方は本番と同じ部品（``yosou.shared.combo_value``）で、重みの推定（``ComboBlendFitter``）と、
    線・上限の選び方（``ComboRuleGrid``）に使う。``sample`` が 1 より大きい券種は、レースID を ``sample`` で割った余りが 0 のレースだけにする
    （3連単は1レース数千組あるので、推定を軽くするため）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, sample: dict[TicketType, int] | None = None) -> None:
        self._con = con
        self._sample = sample or {}
        self._features = ComboBlendFeatures()
        self._folding = PoolFolding()

    def build(self, marked: pd.DataFrame, ticket_types: tuple[TicketType, ...]) -> dict[TicketType, pd.DataFrame]:
        dates = pd.to_datetime(marked["race_date"])
        days = RaceDayRange(dates.min().date(), dates.max().date())
        races = set(marked["race_id"].astype(str))
        strength = HorseStrength().of(marked)
        sources = TrifectaSources().of(split_combo(self._board(TicketType.TRIFECTA, days, races), 3), strength)
        heads = self._races(marked)
        return {ticket_type: self._frame(ticket_type, days, races, sources, strength, heads) for ticket_type in ticket_types}

    def _frame(self, ticket_type: TicketType, days: RaceDayRange, races: set[str], sources: pd.DataFrame, strength: pd.DataFrame,
               heads: pd.DataFrame) -> pd.DataFrame:
        folded = self._folding.fold(ticket_type, sources, [MARKET, HARVILLE])
        frame = self._features.build(ticket_type, self._board(ticket_type, days, races), folded, strength)
        every = self._sample.get(ticket_type, 1)
        if every > 1:
            frame = frame[frame["race_id"].astype(np.int64) % every == 0]
        payouts = PayoutRepository(self._con, ticket_type).read(days)
        paid = payouts.groupby(["race_id", COMBO], as_index=False)[YEN].sum().rename(columns={COMBO: "combo", YEN: PAYOUT})
        frame = frame.merge(paid.assign(race_id=paid["race_id"].astype(str)), on=["race_id", "combo"], how="left")
        frame[PAYOUT] = frame[PAYOUT].fillna(0.0)
        frame[HIT] = frame[PAYOUT] > 0
        return frame.merge(heads, on="race_id", how="left")

    def _board(self, ticket_type: TicketType, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        board = board[board["race_id"].astype(str).isin(races)]
        return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})

    def _races(self, marked: pd.DataFrame) -> pd.DataFrame:
        first = marked.groupby("race_id", sort=False)[["race_date", "expectation", "fold"]].first().reset_index()
        tops = marked[marked["mark"] == "◎"].groupby("race_id")["horse_no"].first().rename("top")
        return first.merge(tops.reset_index(), on="race_id", how="left")
