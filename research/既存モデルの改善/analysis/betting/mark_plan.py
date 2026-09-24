"""印の買い方の、検証期間で決める線の組。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

import pandas as pd

from .candidate_columns import COVER, RACE, TICKET, VALUE
from .race_selector import RaceSelector
from .shaky_favorite import ShakyFavorite


@dataclass(frozen=True)
class MarkPlan:
    """印の買い方で、検証期間で決める線の組。

    - ``races_per_day``: 1開催日に勝負する上位のレース数（重賞は別枠）。None なら全レース。
    - ``shaky_line``: ◎の3着以内の確率がこれより低いと「◎が危うい」として押さえを足す（``ShakyFavorite``）。
    - ``value_lines``: 券種 → 期待値の線。これより期待値の低い買い目はカットする。
    - ``adopted``: テスト期間に買う券種（検証期間の成績で決めた）。

    例: (5, 0.5, {3連複: 1.1, …}, {3連複}) なら、1開催日の上位5レースと重賞で、3連複の買い目のうち期待値 1.1 以上だけを買う。
    """

    races_per_day: int | None
    shaky_line: float
    value_lines: Mapping[str, float] = field(default_factory=dict)
    adopted: frozenset[str] = frozenset()

    def races(self, races: pd.DataFrame) -> pd.DataFrame:
        """勝負するレースの行に、◎が危ういか（押さえを買うか）の列を付けたもの。"""
        chosen = races[RaceSelector(self.races_per_day).select(races)]
        return chosen.assign(**{COVER: ShakyFavorite(self.shaky_line).of(chosen)})

    def base_rows(self, candidates: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """勝負するレースの買い目（押さえは◎が危ういレースだけ）。期待値のカットの前。"""
        chosen = self.races(races)[[RACE, COVER]].rename(columns={COVER: "押さえを買う"})
        rows = candidates.merge(chosen, on=RACE, how="inner")
        return rows[~rows[COVER] | rows["押さえを買う"]].drop(columns="押さえを買う")

    def apply(self, candidates: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """買う買い目: 勝負するレースの、買うと決めた券種の、期待値の線以上の買い目。"""
        rows = self.base_rows(candidates, races)
        lines = rows[TICKET].map(self.value_lines)
        return rows[rows[TICKET].isin(self.adopted) & (rows[VALUE] >= lines)].reset_index(drop=True)

    def with_all_tickets(self) -> MarkPlan:
        """線の決まった券種を全部買う計画（参考: 検証期間で回収率 100% に届かなかった券種も買ったとき）。"""
        return replace(self, adopted=frozenset(self.value_lines))

    def describe(self) -> str:
        per_day = "全レース" if self.races_per_day is None else f"1開催日の上位 {self.races_per_day} レース＋重賞"
        shaky = "◎が人気馬で危険度が正" if self.shaky_line <= 0 else f"◎の3着以内の確率が {self.shaky_line:g} 未満か、◎が人気馬で危険度が正"
        return f"{per_day}。押さえは「{shaky}」のレース"
