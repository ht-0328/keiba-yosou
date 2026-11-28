"""確率を直すモデルの学習に使う、元DB の値（確定オッズ・単勝の払戻・事実表の列）を読む。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import facts as facts_table
from 共通 import keys

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import FinalOddsRepository
from yosou.shared.win_correction import FACT_COLUMNS


@dataclass(frozen=True)
class TrainingInputs:
    """``TrainingTable`` に渡す、元DB から読んだ値。"""

    win_odds: pd.DataFrame
    place_odds: pd.DataFrame
    quinella_odds: pd.DataFrame
    win_payouts: pd.DataFrame
    facts: pd.DataFrame


class TrainingInputReader:
    """期間（``RaceDayRange``）の確定オッズ（単勝・複勝・馬連）と単勝の払戻と、事実表の ``FACT_COLUMNS`` を読む。
    事実表は接続に無ければ作る（``共通.facts.ensure_facts``。全部の期間で数分かかる）。"""

    def read(self, con: duckdb.DuckDBPyConnection, days: RaceDayRange) -> TrainingInputs:
        table = keys.q(facts_table.ensure_facts(con))
        columns = ", ".join(keys.q(column) for column in ("race_id", "horse_no", *FACT_COLUMNS))
        facts = con.execute(f"SELECT {columns} FROM {table} WHERE CAST(race_date AS VARCHAR) BETWEEN ? AND ?",
                            [days.first_day.isoformat(), days.last_day.isoformat()]).df()
        return TrainingInputs(
            win_odds=FinalOddsRepository(con, TicketType.WIN).read(days),
            place_odds=FinalOddsRepository(con, TicketType.PLACE).read(days),
            quinella_odds=FinalOddsRepository(con, TicketType.QUINELLA).read(days),
            win_payouts=PayoutRepository(con, TicketType.WIN).read(days),
            facts=facts,
        )
