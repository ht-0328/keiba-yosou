"""L. 騎手・調教師・血統の市場に対する成績（4個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..history import MarketExcessRate
from ..odds import TOP3_RATE, MarketPlaces

#: 人・血統の列（出走の行と、過去の出走の表の両方にある列） → 特徴量の名前。
PEOPLE_MARKET_COLUMNS: dict[str, str] = {
    "jockey_code": "騎手の市場に対する超過3着以内率",
    "trainer_code": "調教師の市場に対する超過3着以内率",
    "sire": "父の産駒の市場に対する超過3着以内率",
    "damsire": "母の父の産駒の市場に対する超過3着以内率",
}
#: 3着以内とみなす着順のうち、いちばん大きいもの。
_LAST_PLACE = 3


class PeopleMarketFeatures:
    """L. 騎手・調教師・血統の市場に対する成績。

    「その人が乗った（育てた・その血統の）馬が、オッズから期待された3着以内率をどれだけ上回ったか」を、
    開催日の前日までの 365日で数える（``MarketExcessRate``）。C・H の「近1年の3着以内の割合」は、強い馬に
    乗る騎手ほど高くなり、オッズと同じことを言ってしまう。こちらはオッズで説明できない分だけを表す。
    研究「既存モデルの改善」の材料の実験で採用の基準を満たし、2026-09-30 に利用者が採用を決めた。

    過去の出走は ``records.market_runs``（``MarketRunRepository`` が読む）。オッズから見た3着以内率は、
    過去のレースの確定オッズから出す（過去のレースの値なので、リークにならない）。オッズの無い出走は期待 0 で数える。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        runs = self._scored_runs(records.market_runs)
        entries = records.entries
        return pd.DataFrame(
            {name: MarketExcessRate(entries, column).of(runs) for column, name in PEOPLE_MARKET_COLUMNS.items()},
            index=entries.index,
        )

    def _scored_runs(self, market_runs: pd.DataFrame) -> pd.DataFrame:
        """過去の出走に、3着以内か（``placed``）と、オッズから見た3着以内率（``expected``）の列を足す。"""
        expected = MarketPlaces().of(market_runs[["race_id", "win_odds"]])[TOP3_RATE].fillna(0.0)
        placed = pd.to_numeric(market_runs["finish"], errors="coerce").between(1, _LAST_PLACE).astype(float)
        return market_runs.assign(placed=placed, expected=expected)
