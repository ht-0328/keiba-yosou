"""1レースの出走馬の能力指数を出し、高い順に並べる。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .. import card, facts
from .ability_index import ABILITY, AbilityIndex
from .ability_settings import AbilitySettings
from .figure_cache import KEPT, FigureCache
from .run_source import RunSource
from .speed_figure import FIGURE

#: 出走馬の表に足す列。
RANK, THIS_RUN = "順位", "この走の指数"


@dataclass(frozen=True)
class RaceAbilityReport:
    """1レースの結果。``entries`` は1行 = 1頭で、能力指数の高い順（指数の無い馬は最後）。
    ``history`` は出走馬の、今回より前の走（スピード指数つき、新しい順）。``finished`` は成績の確定したレースか。
    """

    rid: str
    header: dict[str, Any]
    entries: pd.DataFrame
    history: pd.DataFrame
    finished: bool


class RaceAbility:
    """``rid`` のレースの出走馬に、能力指数を付ける。これから走るレースにも、終わったレースにも使える。

    過去の走のスピード指数は ``FigureCache`` から読む。今回の走そのものは使わない（終わったレースでも、
    今回より前の走だけから作る）。終わったレースなら、今回の走のスピード指数と着順も並べる（見比べるため）。
    ``condition_code`` は、まだ発表されていない当日の馬場状態（1〜4）を手で与えるときに使う。
    """

    def __init__(self, settings: AbilitySettings, cache: FigureCache) -> None:
        self._settings = settings
        self._cache = cache

    def rank(self, con: duckdb.DuckDBPyConnection, rid: str, condition_code: str | None = None) -> RaceAbilityReport:
        header = card.race_header(con, rid)
        history = self._cache.load(con)
        entries = self._entries(con, rid, condition_code)
        earlier = history[(history["race_id"] != rid) & (history["race_date"] < entries["race_date"].min())]
        combined = pd.concat([earlier, entries.assign(**{FIGURE: np.nan})[list(KEPT)]], ignore_index=True)
        indexed = AbilityIndex(self._settings).build(combined).iloc[len(earlier):]
        this_run = history[history["race_id"] == rid].set_index("horse_id")[FIGURE]
        ranked = entries.join(indexed.drop(columns=list(KEPT)).set_axis(entries.index)).assign(
            **{THIS_RUN: entries["horse_id"].map(this_run)})
        ranked = ranked.sort_values([ABILITY, "horse_no"], ascending=[False, True], na_position="last")
        ranked.insert(0, RANK, ranked[ABILITY].rank(ascending=False, method="min"))
        past = earlier[earlier["horse_id"].isin(entries["horse_id"])].sort_values("race_date", ascending=False)
        return RaceAbilityReport(rid, header, ranked.reset_index(drop=True), past, not this_run.empty)

    def _entries(self, con: duckdb.DuckDBPyConnection, rid: str, condition_code: str | None) -> pd.DataFrame:
        table = facts.build_entry_facts(con, facts.EntryScope(rid, condition_code))
        try:
            return RunSource(con, table).read(date(1900, 1, 1)).reset_index(drop=True)
        finally:
            con.execute(f"DROP TABLE IF EXISTS {table}")
