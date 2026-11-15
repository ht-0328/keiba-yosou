"""過去のレースの推奨買目を、本番と同じ決まり（``RECOMMENDED_PLANS``）で作り直す。

組の確率は本番と同じ 1着・2着・3着の条件つきロジット（研究「地方の万馬券」段5。``PositionModel``）で、係数は本番と同じく 11頭以上のレースで当てはめる。
当てはめ方は、各年を残りの年で当てはめる（入れ替え）か、その年より前の年だけで当てはめる（前の年）。オッズと払戻は確定のもの、組の形は確定の単勝人気、
3連複の荒れ具合は研究「地方の万馬券」段④の予測（2024年以降は学びに使っていない）で付ける。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from 地方の推奨買目.combo_forms import FORM
from 地方の推奨買目.member_predictions import MemberPredictions
from 地方の推奨買目.pool_tables import PoolTables
from 地方の推奨買目.pool_tables_builder import PoolTablesBuilder
from 地方の推奨買目.popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand
from 地方の推奨買目.position_coefficients import PositionCoefficients
from 地方の推奨買目.position_model import EV, PROBABILITY, PositionModel
from 地方の推奨買目.repository import FactsRowsRepository, LocalTicketOddsRepository, TrifectaOddsRepository
from 地方の推奨買目.ticket_plan import RECOMMENDED_PLANS, TicketPlan
from 地方の推奨買目.ticket_probabilities import TICKET_KEYS, TicketProbabilities

from 地方の万馬券.analysis.repository import LocalTicketPayoutRepository, TrifectaResultRepository

from .bulk_plan_chooser import UPSET, BulkPlanChooser

#: 当てはめ方。入れ替え: 各年を残りの年で当てはめる。前の年: その年より前の年だけで当てはめる。本番: 本番の係数をそのまま使う（当てはめない）。
LEAVE_ONE_OUT, FORWARD, PRODUCTION = "入れ替え", "前の年", "本番"
PROTOCOLS: tuple[str, ...] = (LEAVE_ONE_OUT, FORWARD, PRODUCTION)
#: 荒れ具合の予測の列（中荒れ以上の確率）。
_UPSET_COLUMN = "中荒れ以上の確率"
_POOL_TICKETS: tuple[str, ...] = ("馬単", "3連複", "複勝")
_TRIFECTA = "3連単"
_ORDER = {FAVORITE: 0, MIDDLE: 1, LONGSHOT: 2}
#: 推奨買目の表の列。
BET_COLUMNS: tuple[str, ...] = ("race_id", "year", "race_date", "field_size", "ticket", "a", "b", "c", PROBABILITY, "odds", EV, "payout")


@dataclass(frozen=True)
class RecommendedBetsSettings:
    """対象の最初の開催日・全頭の予想の当日の予測の表・3連複の荒れ具合の予測の表（pkl）・当てはめ方・表に入れる最少の頭数・係数を当てはめる最少の頭数。
    当てはめ方が「本番」なら ``coefficients``（本番の係数）を全部の年にそのまま使う。"""

    date_from: date
    predictions: Path
    trio_upsets: Path
    protocol: str = LEAVE_ONE_OUT
    min_heads: int = 5
    fit_min_heads: int = 11
    plans: tuple[TicketPlan, ...] = field(default=RECOMMENDED_PLANS)
    coefficients: PositionCoefficients | None = None


class RecommendedBetsBuilder:
    """``build()`` は (推奨買目の表（1行 = 1点。``BET_COLUMNS``）, レースの表（``race_id``・``year``・``race_date``・``field_size``。買わなかったレースも入る))。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, settings: RecommendedBetsSettings) -> None:
        self._con = con
        self._settings = settings

    def build(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        s = self._settings
        runners = self._runners()
        races = runners.groupby("race_id")[["year", "race_date", "field_size"]].first().reset_index()
        upsets = pd.read_pickle(s.trio_upsets)[["race_id", _UPSET_COLUMN]].rename(columns={_UPSET_COLUMN: UPSET})
        upsets["race_id"] = upsets["race_id"].astype("int64")
        years = sorted(races["year"].unique())
        pools = {year: self._pools(runners[runners["year"] == year]) for year in years}
        large = set(races.loc[races["field_size"] >= s.fit_min_heads, "race_id"])
        model = PositionModel()
        parts, kept_races = [], []
        for year in years:
            if s.protocol == PRODUCTION:
                if s.coefficients is None:
                    raise ValueError("当てはめ方が「本番」のときは本番の係数を渡してください")
                coefficients = s.coefficients
            else:
                fit_years = [y for y in years if (y < year if s.protocol == FORWARD else y != year)]
                if not fit_years:
                    continue
                coefficients = model.fit([_subset(pools[y], large) for y in fit_years])
            combos = model.predict(pools[year], coefficients)
            year_runners = runners[runners["year"] == year]
            year_races = races[races["year"] == year]
            parts.append(self._year_bets(combos, year_runners, year_races, upsets))
            kept_races.append(year_races)
            print(f"{year}年: 推奨買目 {len(parts[-1]):,} 点（{parts[-1]['race_id'].nunique():,} / {len(year_races):,} レース）", flush=True)
        return pd.concat(parts, ignore_index=True), pd.concat(kept_races, ignore_index=True)

    def _year_bets(self, combos: pd.DataFrame, runners: pd.DataFrame, races: pd.DataFrame, upsets: pd.DataFrame) -> pd.DataFrame:
        probabilities = TicketProbabilities().of(combos, runners[["race_id", "horse_no", "frame_no"]])
        bands = self._bands(runners)
        chooser = BulkPlanChooser()
        chosen = []
        for plan in self._settings.plans:
            table = self._priced(plan.ticket, probabilities[plan.ticket], combos, races["race_id"])
            table = table.merge(races[["race_id", "year", "race_date", "field_size"]], on="race_id", how="inner")
            if plan.form:
                table = self._with_form(table, bands, TICKET_KEYS[plan.ticket])
            if plan.upset_min > 0:
                table = table.merge(upsets, on="race_id", how="left")
            picked = chooser.choose(plan, table).assign(ticket=plan.ticket)
            for name in ("b", "c"):
                if name not in picked.columns:
                    picked[name] = np.nan
            chosen.append(picked[list(BET_COLUMNS)])
        return pd.concat(chosen, ignore_index=True)

    def _priced(self, ticket: str, probabilities: pd.DataFrame, combos: pd.DataFrame, race_ids: pd.Series) -> pd.DataFrame:
        """組の確率に確定オッズと払戻（外れは 0）を付ける。複勝・ワイドのオッズは幅の真ん中。"""
        if ticket == _TRIFECTA:
            return combos.rename(columns={"first": "a", "second": "b", "third": "c"})[["race_id", "a", "b", "c", PROBABILITY, "odds", "payout"]]
        keys = ["race_id", *TICKET_KEYS[ticket]]
        odds = LocalTicketOddsRepository(self._con, ticket).load(race_ids)
        if "odds" not in odds.columns:
            odds = odds.assign(odds=(odds["odds_lo"].astype(float) + odds["odds_hi"].astype(float)) / 2.0)
        payouts = LocalTicketPayoutRepository(self._con, ticket).load(race_ids)
        table = probabilities.merge(odds[[*keys, "odds"]], on=keys, how="inner").merge(payouts, on=keys, how="left")
        table["payout"] = table["payout"].fillna(0).astype(int)
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
        results = TrifectaResultRepository(self._con).load()
        trifecta = trifecta.merge(results[["race_id", "first", "second", "third", "payout"]], on=["race_id", "first", "second", "third"], how="left")
        exacta, trio, place = (LocalTicketOddsRepository(self._con, ticket).load(ids) for ticket in _POOL_TICKETS)
        return PoolTablesBuilder().build(horses, trifecta, exacta, trio, place)

    @staticmethod
    def _bands(runners: pd.DataFrame) -> pd.DataFrame:
        """馬ごとの人気の帯（確定の単勝人気）。"""
        bands = PopularityBand().band_of(pd.to_numeric(runners["popularity"], errors="coerce")).fillna(LONGSHOT).astype(str)
        return pd.DataFrame({"race_id": runners["race_id"].to_numpy(), "horse_no": runners["horse_no"].astype(int).to_numpy(), "band": bands.to_numpy()})

    @staticmethod
    def _with_form(table: pd.DataFrame, bands: pd.DataFrame, keys: tuple[str, ...]) -> pd.DataFrame:
        """組の形（本番の ``ComboForms`` と同じ、人気の帯を 人・中・大 の順に並べた文字）。"""
        letters = []
        for key in keys:
            merged = table[["race_id", key]].merge(bands.rename(columns={"horse_no": key}), on=["race_id", key], how="left")
            letters.append(merged["band"].fillna(LONGSHOT).to_numpy())
        stacked = np.vstack(letters).T if len(table) else np.empty((0, len(keys)))
        return table.assign(**{FORM: ["".join(sorted(row, key=_ORDER.get)) for row in stacked]})


def _subset(tables: PoolTables, race_ids: set[int]) -> PoolTables:
    """``race_ids`` のレースだけの票の表。"""
    def keep(table: pd.DataFrame) -> pd.DataFrame:
        return table[np.isin(table["race_id"].to_numpy(), list(race_ids))]
    return PoolTables(keep(tables.horses), keep(tables.pairs), keep(tables.combos))
