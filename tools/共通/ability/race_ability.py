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
from .first_conditions import FirstConditions
from .pedigree_aptitude import PEDIGREE, PedigreeAptitude
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
    血統で補う設定なら、初めての条件の馬に、産駒の過去の走から作った値を足す（``PedigreeAptitude``）。
    産駒の走から作った表は、同じ過去の走の表のあいだは覚えておき、レースごとに作り直さない（``--all`` や検索画面で速くするため）。
    """

    def __init__(self, settings: AbilitySettings, cache: FigureCache) -> None:
        self._settings = settings
        self._cache = cache
        self._fitted: tuple[pd.DataFrame, PedigreeAptitude] | None = None

    def rank(self, con: duckdb.DuckDBPyConnection, rid: str, condition_code: str | None = None) -> RaceAbilityReport:
        header = card.race_header(con, rid)
        history = self._cache.load(con)
        entries = self._entries(con, rid, condition_code)
        # 能力指数はその馬自身の走だけから作るので、出走馬の走だけに絞ってから作る（DB 全体を並べ替えると十数秒かかる）。
        mine = history[history["horse_id"].isin(entries["horse_id"])][list(KEPT)]
        earlier = mine[(mine["race_id"] != rid) & (mine["race_date"] < entries["race_date"].min())]
        combined = pd.concat([earlier, entries.assign(**{FIGURE: np.nan})[list(KEPT)]], ignore_index=True)
        indexed = self._index(combined, history).iloc[len(earlier):]
        this_run = mine[mine["race_id"] == rid].set_index("horse_id")[FIGURE]
        ranked = entries.join(indexed.drop(columns=list(KEPT)).set_axis(entries.index)).assign(
            **{THIS_RUN: entries["horse_id"].map(this_run)})
        ranked = ranked.sort_values([ABILITY, "horse_no"], ascending=[False, True], na_position="last")
        ranked.insert(0, RANK, ranked[ABILITY].rank(ascending=False, method="min"))
        past = earlier.sort_values("race_date", ascending=False)
        return RaceAbilityReport(rid, header, ranked.reset_index(drop=True), past, not this_run.empty)

    def _index(self, combined: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
        indexed = AbilityIndex(self._settings).build(combined)
        if not self._settings.pedigree:
            return indexed
        flagged = FirstConditions(self._settings).build(indexed)
        return self._pedigree(history).fill(flagged)

    def _pedigree(self, history: pd.DataFrame) -> PedigreeAptitude:
        """過去の全部の走（補う前の能力指数に戻したもの）から、血統の値の表を作る。同じ表なら作り直さない。"""
        if self._fitted is not None and self._fitted[0] is history:
            return self._fitted[1]
        before = history.assign(**{ABILITY: history[ABILITY] - history[PEDIGREE]})
        fitted = PedigreeAptitude(self._settings).fit(before)
        self._fitted = (history, fitted)
        return fitted

    def _entries(self, con: duckdb.DuckDBPyConnection, rid: str, condition_code: str | None) -> pd.DataFrame:
        table = facts.build_entry_facts(con, facts.EntryScope(rid, condition_code))
        try:
            return RunSource(con, table).read(date(1900, 1, 1)).reset_index(drop=True)
        finally:
            con.execute(f"DROP TABLE IF EXISTS {table}")
