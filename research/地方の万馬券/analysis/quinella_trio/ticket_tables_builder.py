"""馬連・3連複の組の表を年ごとに作る: 段5 の条件つきロジット（各年を残りの年で当てはめ、前の年だけでも当てはめる）で組の確率を出し、
確定オッズ・払戻・期待値と、組の形（人気の帯・◎ を含むか）を付ける。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from 地方の推奨買目.member_predictions import MemberPredictions
from 地方の推奨買目.pool_tables import PoolTables
from 地方の推奨買目.pool_tables_builder import PoolTablesBuilder
from 地方の推奨買目.position_model import PROBABILITY, PositionModel
from 地方の推奨買目.repository import FactsRowsRepository, LocalTicketOddsRepository, TrifectaOddsRepository
from 地方の推奨買目.ticket_probabilities import TICKET_KEYS, TicketProbabilities

from ..popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand
from ..repository import LocalTicketPayoutRepository

#: 調べる券種。
TICKETS: tuple[str, ...] = ("馬連", "3連複")
#: 表の列: 前の年だけで当てはめた確率と期待値、組の形、◎ を含むか、◎ の単勝の期待値。
P_FORWARD, EV_FORWARD = "P_forward", "ev_forward"
FORM, HAS_TOP, TOP_VALUE = "form", "has_top", "top_value"
_POOL_TICKETS: tuple[str, ...] = ("馬単", "3連複", "複勝")
#: ◎ を決める単勝オッズの上限（通知の印の決まりと同じ）。
_TOP_MAX_ODDS = 30.0
_BAND_ORDER = {FAVORITE: 0, MIDDLE: 1, LONGSHOT: 2}
#: 段4: 票の見立てを使わない特徴量（全頭の予想のモデルごとの 1着・3着以内の確率だけ）。市場と別の情報源になるかを見る。
POOL_FREE_FIRST: tuple[str, ...] = ("log_p1_lgb", "log_p1_cat")
POOL_FREE_SECOND: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat")
POOL_FREE_THIRD: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat")


@dataclass(frozen=True)
class QuinellaTrioSettings:
    """対象の最初の開催日・全頭の予想の予測の表の置き場所・最少の頭数（表には全部入れ、頭数の線は買い方で引く）・票の見立てを使わないか。"""

    date_from: date
    predictions: Path
    min_heads: int = 5
    pool_free: bool = False


class QuinellaTrioTablesBuilder:
    def __init__(self, con, settings: QuinellaTrioSettings) -> None:
        self._con = con
        self._settings = settings

    def _model(self) -> PositionModel:
        if self._settings.pool_free:
            return PositionModel(POOL_FREE_FIRST, POOL_FREE_SECOND, POOL_FREE_THIRD)
        return PositionModel()

    def build(self) -> dict[str, pd.DataFrame]:
        """券種 → 組の表（``race_id``・``a``・``b``（・``c``）・``P``・``odds``・``payout``・``ev``・``P_forward``・``ev_forward``・
        ``year``・``race_date``・``field_size``・``form``・``has_top``・``top_value``）。"""
        runners = self._runners()
        years = sorted(runners["year"].unique())
        pools = {year: self._pools(runners[runners["year"] == year]) for year in years}
        model = self._model()
        parts: dict[str, list[pd.DataFrame]] = {ticket: [] for ticket in TICKETS}
        for year in years:
            tables = self._year_tables(model, pools, years, year, runners[runners["year"] == year])
            for ticket in TICKETS:
                parts[ticket].append(tables[ticket])
        return {ticket: pd.concat(frames, ignore_index=True) for ticket, frames in parts.items()}

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

    def _year_tables(self, model: PositionModel, pools: dict, years: list, year: int, runners: pd.DataFrame) -> dict[str, pd.DataFrame]:
        frames = runners[["race_id", "horse_no", "frame_no"]]
        loo = model.fit([pools[y] for y in years if y != year])
        probabilities = TicketProbabilities().of(model.predict(pools[year], loo), frames)
        earlier = [pools[y] for y in years if y < year]
        forward = TicketProbabilities().of(model.predict(pools[year], model.fit(earlier)), frames) if earlier else None
        races = runners.groupby("race_id")[["race_date", "field_size"]].first().reset_index()
        traits = self._horse_traits(runners)
        out = {}
        for ticket in TICKETS:
            keys = ["race_id", *TICKET_KEYS[ticket]]
            table = self._priced(ticket, probabilities[ticket], keys)
            if forward is not None:
                table = table.merge(forward[ticket].rename(columns={PROBABILITY: P_FORWARD}), on=keys, how="left")
            else:
                table[P_FORWARD] = np.nan
            table[EV_FORWARD] = table[P_FORWARD] * table["odds"]
            table = table.merge(races, on="race_id", how="left").assign(year=year)
            out[ticket] = self._with_form(table, traits, TICKET_KEYS[ticket])
        return out

    def _priced(self, ticket: str, probabilities: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        ids = probabilities["race_id"].drop_duplicates()
        odds = LocalTicketOddsRepository(self._con, ticket).load(ids)
        payouts = LocalTicketPayoutRepository(self._con, ticket).load(ids)
        table = probabilities.merge(odds, on=keys, how="inner").merge(payouts, on=keys, how="left")
        table["payout"] = table["payout"].fillna(0).astype(int)
        table["ev"] = table[PROBABILITY] * table["odds"].astype(float)
        return table

    @staticmethod
    def _horse_traits(runners: pd.DataFrame) -> pd.DataFrame:
        """馬ごとの人気の帯と、◎（単勝 30倍以下で 1着の確率 × 単勝オッズ が1位）かどうか・その期待値。"""
        traits = runners[["race_id", "horse_no", "popularity", "p1", "win_odds"]].copy()
        traits["band"] = PopularityBand().band_of(traits["popularity"]).fillna(LONGSHOT)
        value = (traits["p1"] * traits["win_odds"]).where(traits["win_odds"] <= _TOP_MAX_ODDS, -1.0)
        traits["value"] = value
        best = traits.sort_values("value", ascending=False).groupby("race_id").head(1)
        traits["is_top"] = traits.index.isin(best.index) & (traits["value"] > 0)
        top_value = best.set_index("race_id")["value"]
        traits[TOP_VALUE] = traits["race_id"].map(top_value)
        return traits[["race_id", "horse_no", "band", "is_top", TOP_VALUE]]

    @staticmethod
    def _with_form(table: pd.DataFrame, traits: pd.DataFrame, keys: tuple[str, ...]) -> pd.DataFrame:
        """組の形（人気の帯を 人・中・大 の順に並べた文字。例 ``人中大``）と ◎ を含むか。"""
        bands = []
        has_top = np.zeros(len(table), dtype=bool)
        for key in keys:
            merged = table[["race_id", key]].merge(traits.rename(columns={"horse_no": key}), on=["race_id", key], how="left")
            bands.append(merged["band"].fillna(LONGSHOT).to_numpy())
            has_top |= merged["is_top"].fillna(False).to_numpy().astype(bool)
            table[TOP_VALUE] = merged[TOP_VALUE].to_numpy()
        stacked = np.vstack(bands).T
        table[FORM] = ["".join(sorted(row, key=_BAND_ORDER.get)) for row in stacked]
        table[HAS_TOP] = has_top
        return table
