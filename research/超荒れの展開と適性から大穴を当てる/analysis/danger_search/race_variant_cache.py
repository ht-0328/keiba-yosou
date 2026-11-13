"""レースごとの「消の組」ごとに、印を付けた行と買い目（払戻・トリガミつき）を覚えておく。"""

from __future__ import annotations

import sys
import time

import pandas as pd

from 今週の予想.filter_columns import AGREEMENT, POOL_BACKED, member_columns
from 今週の予想.forecast_columns import IS_DANGER, MARK, MARKET_WIN, WIN_ODDS, WIN_VALUE, WIN_VALUE_BAND
from 今週の予想.mark_tickets import RULE
from 今週の予想.torigami_filter import DROPPED, TorigamiFilter

from 印の成績.ticket_payouts import PAYOUT

from .odds_cache import OddsCache
from .payout_table import PayoutTable
from .race_variant_workers import RaceVariantWorkers
from .search_inputs import SearchInputs

#: 消の組の列（消にした馬のIDを ``|`` でつないだもの。消が無ければ空文字）。
KEY = "key"
#: 覚えておく印の行の列（組の期待値の買い目を選ぶ ``races``・``ComboRaceTraits`` が使うものだけ）。
MARKED_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", "horse_no", MARK, WIN_VALUE_BAND, AGREEMENT, POOL_BACKED, "field_size",
                                   WIN_ODDS, WIN_VALUE, MARKET_WIN, IS_DANGER, *member_columns(WIN_VALUE))
#: 覚えておく買い目の列（成績を数えるのに要るものだけ。外した買い目は覚えない）。
TICKET_COLUMNS: tuple[str, ...] = ("race_id", "race_date", RULE, "ticket_type", "stake_units", PAYOUT)


class RaceVariantCache:
    """消の判定（``FavoriteDangerJudge`` などの戻り値）を受け取り、レースごとの消の組（``KEY``）がまだ無ければ、そのレースだけ
    道具「印の成績」と同じ流れ（``BacktestMarker.mark`` → 荒れ具合 → ``MarkTickets`` → 払戻・オッズ → ``TorigamiFilter``）で印と買い目を作って覚える。
    印付けと買い目は複数のプロセスで分けて行い（``RaceVariantWorkers``）、払戻・オッズ（元DB）とトリガミはこのプロセスで付ける。
    ``assemble`` は、その判定での全レースの印の行と買い目（買う点だけ）を返す。

    レースの印と買い目は、そのレースの行と消の組だけで決まる（ほかのレースに依らない）ので、消の決め方を替えても変わったレースだけ数え直せる。
    """

    def __init__(self, inputs: SearchInputs, payouts: PayoutTable, odds: OddsCache, workers: int | None = None) -> None:
        self._inputs = inputs
        self._payouts = payouts
        self._odds = odds
        self._workers = RaceVariantWorkers(inputs.tested, inputs.places, inputs.wins, inputs.upset, inputs.models, workers)
        self._filter = TorigamiFilter()
        self._done: set[tuple[str, str]] = set()
        self._marked_parts: list[pd.DataFrame] = []
        self._ticket_parts: list[pd.DataFrame] = []
        self._marked_all: pd.DataFrame | None = None
        self._tickets_all: pd.DataFrame | None = None

    def close(self) -> None:
        self._workers.close()

    def keys_of(self, dangers: pd.DataFrame) -> pd.DataFrame:
        """印を付ける全レースの消の組（列 ``race_id``・``KEY``）。"""
        flagged = dangers[dangers["is_danger"].astype(bool)].astype({"race_id": str, "horse_id": str})
        keys = flagged.sort_values("horse_id").groupby("race_id")["horse_id"].agg("|".join)
        races = self._inputs.race_ids.astype(str)
        return pd.DataFrame({"race_id": races, KEY: races.map(keys).fillna("")})

    def ensure(self, dangers: pd.DataFrame) -> int:
        """まだ無いレースの消の組ぶんの印と買い目を作って覚える。作ったレースの数を返す。"""
        keys = self.keys_of(dangers)
        missing = keys[[(race, key) not in self._done for race, key in zip(keys["race_id"], keys[KEY])]]
        if missing.empty:
            return 0
        started = time.monotonic()
        races = missing["race_id"].tolist()
        key_of = dict(zip(missing["race_id"], missing[KEY]))
        chosen = dangers[dangers["race_id"].astype(str).isin(set(races))]
        finished = 0
        for marked, tickets in self._workers.build(races, chosen):
            self._store(marked, tickets, key_of)
            finished += marked["race_id"].nunique()
            print(f"  印と買い目: {finished:,} / {len(races):,} レース（{time.monotonic() - started:.0f}秒）", file=sys.stderr, flush=True)
        self._done.update(key_of.items())
        self._marked_all = self._tickets_all = None
        return len(races)

    def assemble(self, dangers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """その判定での全レースの（印の行（``MARKED_COLUMNS``）, 買う買い目（``TICKET_COLUMNS``））。先に ``ensure`` を呼ぶ。"""
        keys = self.keys_of(dangers)
        if self._marked_all is None:
            self._marked_all = pd.concat(self._marked_parts, ignore_index=True)
            self._tickets_all = pd.concat(self._ticket_parts, ignore_index=True)
        marked = self._marked_all.merge(keys, on=["race_id", KEY], how="inner")
        tickets = self._tickets_all.merge(keys, on=["race_id", KEY], how="inner")
        return marked.drop(columns=[KEY]), tickets.drop(columns=[KEY])

    def _store(self, marked: pd.DataFrame, tickets: pd.DataFrame, key_of: dict[str, str]) -> None:
        tickets = self._filter.apply(self._odds.attach(self._payouts.attach(tickets)))
        marked = marked.assign(**{KEY: marked["race_id"].astype(str).map(key_of)})
        bought = tickets[tickets[DROPPED] == ""]
        bought = bought.assign(**{KEY: bought["race_id"].astype(str).map(key_of)})
        self._marked_parts.append(marked[[*MARKED_COLUMNS, KEY]].reset_index(drop=True))
        self._ticket_parts.append(bought[[*TICKET_COLUMNS, KEY]].reset_index(drop=True))
