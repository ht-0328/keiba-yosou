"""騎手・調教師・父・母父が、オッズから期待された3着以内率をどれだけ上回ったか。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature.history import AsOfLookup, DatedRecords
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

#: 人・血統の列 → 特徴量の名前。
PEOPLE: dict[str, str] = {
    "jockey_code": "騎手の市場に対する超過3着以内率",
    "trainer_code": "調教師の市場に対する超過3着以内率",
    "sire": "父の産駒の市場に対する超過3着以内率",
    "damsire": "母の父の産駒の市場に対する超過3着以内率",
}
NAMES: tuple[str, ...] = tuple(PEOPLE.values())
#: 数える期間（開催日の前日までの 365日）と、件数の少ない人の値を 0 に寄せる強さ（この件数ぶん 0 を足す）。
_WINDOW_DAYS = 365
_SHRINK = 50.0


class PeopleMarketExcessFeatures:
    """騎手・調教師・血統の表し方（既存モデルの修正計画の 2「騎手・調教師・血統」）。

    名前ではなく、「その人が乗った（育てた・その血統の）馬が、オッズから期待された3着以内率をどれだけ上回ったか」を
    数値にする。強い馬に乗っているだけの騎手は、期待も高いので超過は大きくならない。
    超過 = (3着以内の数 − オッズから見た3着以内率の和) ÷ (出走数 + 50)。件数が少ないと 0 に近づく。
    開催日の前日までの 365日だけで数える。
    """

    def build(self, history: pd.DataFrame) -> pd.DataFrame:
        """列は race_id・horse_id と ``NAMES``。"""
        expected = MarketPlaces().of(history[["race_id", "win_odds"]])[TOP3_RATE].fillna(0.0)
        placed = pd.to_numeric(history["finish"], errors="coerce").between(1, 3).astype(float)
        runs = history.assign(placed=placed.to_numpy(), expected=expected.to_numpy())
        rates = {name: self._rate(runs, column) for column, name in PEOPLE.items()}
        return history[["race_id", "horse_id"]].assign(**rates)

    def _rate(self, runs: pd.DataFrame, column: str) -> pd.Series:
        """1つの人・血統の列の、出走の行ごとの超過率。"""
        days = runs.groupby([column, "race_date"], as_index=False).agg(
            starts=("placed", "size"), placed=("placed", "sum"), expected=("expected", "sum"))
        ordered = days.sort_values([column, "race_date"]).reset_index(drop=True)
        totals = ordered.groupby(column, sort=False)[["starts", "placed", "expected"]].cumsum()
        dated = DatedRecords(totals.assign(**{column: ordered[column], "race_date": ordered["race_date"]}), column, "race_date")
        lookup = AsOfLookup(runs[[column, "race_date"]], column)
        until = lookup.latest(dated, days_before=1).fillna(0.0)
        before = lookup.latest(dated, days_before=_WINDOW_DAYS + 1).fillna(0.0)
        starts = until["starts"] - before["starts"]
        excess = (until["placed"] - before["placed"]) - (until["expected"] - before["expected"])
        rate = excess / (starts + _SHRINK)
        return rate.where(runs[column].notna().to_numpy()).to_numpy()
