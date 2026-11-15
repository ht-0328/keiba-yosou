"""印の組の表: 印の組（``MarkCombos``）に、各年を残りの年で当てはめた 1着・2着・3着の条件つきロジット（研究「地方の万馬券」段5。本番の推奨買目と同じ
``PositionModel``）の組の確率と期待値を付ける。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from 地方の推奨買目.member_predictions import MemberPredictions
from 地方の推奨買目.pool_tables import PoolTables
from 地方の推奨買目.pool_tables_builder import PoolTablesBuilder
from 地方の推奨買目.position_model import PROBABILITY, PositionModel
from 地方の推奨買目.repository import FactsRowsRepository, LocalTicketOddsRepository, TrifectaOddsRepository
from 地方の推奨買目.ticket_probabilities import TicketProbabilities

from 地方の万馬券.analysis.repository import LocalTicketPayoutRepository

from .reverse_combos import REVERSE_RULE, ReverseCombos

#: 票の見立てに使う券種（3連単は別のリポジトリ）。
_POOL_TICKETS: tuple[str, ...] = ("馬単", "3連複", "複勝")
_EXACTA = "馬単"
#: 期待値の列。
EV = "ev"
#: 当てはめ方。入れ替え: 各年を残りの年で当てはめる。前の年: その年より前の年だけで当てはめる（最初の年は表に入れない）。
LEAVE_ONE_OUT, FORWARD = "入れ替え", "前の年"
PROTOCOLS: tuple[str, ...] = (LEAVE_ONE_OUT, FORWARD)


@dataclass(frozen=True)
class MarkTableSettings:
    """対象の最初の開催日・全頭の予想の予測の表（当日。対象の期間を全部含むもの）・表に入れる最少の頭数・係数を当てはめるレースの最少の頭数
    （本番の係数 ``fit.py`` と同じ 11頭）・当てはめ方。"""

    date_from: date
    predictions: Path
    min_heads: int = 5
    fit_min_heads: int = 11
    protocol: str = LEAVE_ONE_OUT


class MarkTableBuilder:
    def __init__(self, con: duckdb.DuckDBPyConnection, settings: MarkTableSettings) -> None:
        self._con = con
        self._settings = settings

    def build(self, marks: pd.DataFrame) -> pd.DataFrame:
        """``marks``（``MarkCombos`` の表）に馬単の裏の行を足し、``year``・``field_size``・``P``・``ev`` を付けた表。確率を出せない組（オッズの無い馬がいるレースなど）は落とす。"""
        runners = self._runners()
        years = sorted(runners["year"].unique())
        pools = {year: self._pools(runners[runners["year"] == year]) for year in years}
        large = set(runners.loc[runners["field_size"] >= self._settings.fit_min_heads, "race_id"])
        all_marks = pd.concat([marks, ReverseCombos().of(marks)], ignore_index=True)
        model = PositionModel()
        parts = []
        forward = self._settings.protocol == FORWARD
        for year in years:
            fit_years = [y for y in years if (y < year if forward else y != year)]
            if not fit_years:
                continue
            coefficients = model.fit([_subset(pools[y], large) for y in fit_years])
            year_runners = runners[runners["year"] == year]
            probabilities = TicketProbabilities().of(model.predict(pools[year], coefficients), year_runners[["race_id", "horse_no", "frame_no"]])
            year_marks = all_marks[all_marks["race_id"].isin(set(year_runners["race_id"]))]
            parts.append(self._attach(year_marks, probabilities).assign(year=year))
            print(f"{year}年: 印の組 {len(parts[-1]):,} 点に確率を付けました", flush=True)
        table = pd.concat(parts, ignore_index=True)
        sizes = runners.groupby("race_id")["field_size"].first()
        table["field_size"] = table["race_id"].map(sizes).astype(int)
        table[EV] = table[PROBABILITY] * table["odds"]
        return table

    def _runners(self) -> pd.DataFrame:
        s = self._settings
        rows = FactsRowsRepository(self._con).load(s.date_from, s.min_heads)
        rows = rows.assign(race_id=rows["race_id"].astype(str))
        rows = rows.merge(MemberPredictions(s.predictions).load(), on=["race_id", "horse_no"], how="inner")
        rows["year"] = pd.to_datetime(rows["race_date"]).dt.year
        return rows.assign(race_id=rows["race_id"].astype("int64")).reset_index(drop=True)

    def _pools(self, horses: pd.DataFrame) -> PoolTables:
        ids = horses["race_id"].drop_duplicates()
        trifecta = TrifectaOddsRepository(self._con).load(ids)
        exacta, trio, place = (LocalTicketOddsRepository(self._con, ticket).load(ids) for ticket in _POOL_TICKETS)
        return PoolTablesBuilder().build(horses, trifecta, exacta, trio, place)

    def _attach(self, marks: pd.DataFrame, probabilities: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """券種ごとに組の確率を付ける。裏の行には、馬単の確定オッズと払戻（外れは 0）も付ける。"""
        parts = []
        for ticket, rows in marks.groupby("ticket"):
            keys = ["race_id", "a", "b", "c"][:1 + _width(str(ticket))]
            joined = rows.merge(probabilities[str(ticket)][[*keys, PROBABILITY]], on=keys, how="inner")
            if ticket == _EXACTA:
                joined = self._price_reverse(joined)
            parts.append(joined)
        return pd.concat(parts, ignore_index=True)

    def _price_reverse(self, exacta: pd.DataFrame) -> pd.DataFrame:
        reverse = exacta["rule"] == REVERSE_RULE
        if not reverse.any():
            return exacta
        ids = exacta.loc[reverse, "race_id"].drop_duplicates()
        odds = LocalTicketOddsRepository(self._con, _EXACTA).load(ids)
        payouts = LocalTicketPayoutRepository(self._con, _EXACTA).load(ids)
        priced = exacta[reverse].drop(columns=["odds", "payout"]).merge(odds, on=["race_id", "a", "b"], how="inner")
        priced = priced.merge(payouts, on=["race_id", "a", "b"], how="left")
        priced["payout"] = priced["payout"].fillna(0).astype(float)
        return pd.concat([exacta[~reverse], priced[exacta.columns]], ignore_index=True)


def _width(ticket: str) -> int:
    """券種の組の馬の数。"""
    return 3 if ticket.startswith("3連") else 1 if ticket in ("単勝", "複勝") else 2


def _subset(tables: PoolTables, race_ids: set[int]) -> PoolTables:
    """``race_ids`` のレースだけの票の表。"""
    def keep(table: pd.DataFrame) -> pd.DataFrame:
        return table[np.isin(table["race_id"].to_numpy(), list(race_ids))]
    return PoolTables(keep(tables.horses), keep(tables.pairs), keep(tables.combos))
