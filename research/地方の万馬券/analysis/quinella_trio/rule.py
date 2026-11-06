"""馬連・3連複の買い方の候補: オッズの帯・期待値の線・頭数・点数の上限（確率か期待値の高い順）・組の形・荒れ具合の条件で組を選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 地方の推奨買目.position_model import EV, PROBABILITY

from .ticket_tables_builder import FORM, HAS_TOP

#: 組の形の指定: ``TOP_FORM`` は ◎ を含む組。人気の帯の文字（例 ``人中大``）は ``|`` で複数を並べられる。
TOP_FORM = "◎"


@dataclass(frozen=True)
class QuinellaTrioRule:
    ticket: str
    ev_min: float = 1.0
    odds_min: float = 0.0
    odds_max: float = float("inf")
    min_heads: int = 0
    #: 1レースの点数の上限（0 なら上限なし）。``order`` の列の高い順に残す。
    top_k: int = 0
    order: str = PROBABILITY
    form: str = ""
    #: 荒れ具合の条件（列の名前と最小値。列が無ければ条件なし）。``upset_max`` を付けると上限（固いレースだけ）。
    upset_column: str = ""
    upset_min: float = 0.0
    upset_max: float = float("inf")

    @property
    def label(self) -> str:
        parts = [self._band(), f"期待値 {self.ev_min:g} 以上"]
        if self.min_heads:
            parts.append(f"{self.min_heads}頭以上")
        if self.top_k:
            parts.append(f"{'確率' if self.order == PROBABILITY else '期待値'}の上位 {self.top_k} 点")
        if self.form == TOP_FORM:
            parts.append("◎ を含む")
        elif self.form:
            parts.append(f"型 {self.form.replace('|', '・')}")
        if self.upset_column:
            upper = f"〜{self.upset_max:g}" if np.isfinite(self.upset_max) else ""
            parts.append(f"{self.upset_column} {self.upset_min:g}{upper}")
        return "・".join(parts)

    def choose(self, table: pd.DataFrame) -> pd.DataFrame:
        """``table`` は組の表（``P``・``odds``・``ev``・``field_size``・``form``・``has_top``・荒れ具合の列）。選んだ組を返す。"""
        kept = table[(table[EV] >= self.ev_min) & (table["odds"] >= self.odds_min) & (table["odds"] <= self.odds_max)]
        kept = kept[kept["field_size"] >= self.min_heads]
        kept = self._by_form(kept)
        kept = self._by_upset(kept)
        if self.top_k:
            kept = kept.sort_values(self.order, ascending=False).groupby("race_id").head(self.top_k)
        return kept.reset_index(drop=True)

    def _by_form(self, table: pd.DataFrame) -> pd.DataFrame:
        if not self.form:
            return table
        if self.form == TOP_FORM:
            return table[table[HAS_TOP]]
        return table[table[FORM].isin(self.form.split("|"))]

    def _by_upset(self, table: pd.DataFrame) -> pd.DataFrame:
        if not self.upset_column or self.upset_column not in table.columns:
            return table
        return table[(table[self.upset_column] >= self.upset_min) & (table[self.upset_column] <= self.upset_max)]

    def _band(self) -> str:
        if self.odds_min <= 0 and np.isinf(self.odds_max):
            return "全部"
        if self.odds_min <= 0:
            return f"〜{self.odds_max:g}倍"
        if np.isinf(self.odds_max):
            return f"{self.odds_min:g}倍〜"
        return f"{self.odds_min:g}〜{self.odds_max:g}倍"
