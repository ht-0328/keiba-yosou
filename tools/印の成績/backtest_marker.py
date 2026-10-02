"""終わったレースの予測に、今週の予想と同じ決め方で印を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_HIGH, PLACE_ODDS_LOW
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE, MarketPlaces
from yosou.shared.place_value import PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator

from 今週の予想.mark_rule import MarkRule

#: 印を付けた表に残す、結果の列。
RESULT_COLUMNS: tuple[str, ...] = ("finish", "popularity", "win_odds", "win_payout", "place_payout", "fold")


class BacktestMarker:
    """全頭の予想の予測（3着以内に入る確率）と、レースの結果・確定オッズ・危険な人気馬の判定から、レースごとに ◎○▲△☆注消 を付ける。

    市場の見立て（オッズから見た3着以内率）と複勝の期待値は、今週の予想と同じ部品で、確定オッズから出す。
    ``estimator`` は複勝の見込みの倍率（全頭の予想の学習済みモデルと一緒に保存した ``place_price.json``）。無ければ期待値は出さず、☆ は付かない。
    """

    def __init__(self, estimator: PlacePriceEstimator | None) -> None:
        self._estimator = estimator
        self._marks = MarkRule()

    def places(self, results: pd.DataFrame) -> pd.DataFrame:
        """出走の行に、オッズから見た勝率・2着以内率・3着以内率を付ける（レースの全頭で出す）。"""
        return pd.concat([results, MarketPlaces().of(results[["race_id", "win_odds"]]).set_axis(results.index)], axis=1)

    def mark(self, predictions: pd.DataFrame, places: pd.DataFrame, dangers: pd.DataFrame) -> pd.DataFrame:
        """``predictions`` はテスト期間の全頭の予想の行、``places`` は ``places`` の戻り値、``dangers`` は危険な人気馬の判定。

        戻り値は1行 = 1頭。列は race_id・race_date と ``MarkRule.assign`` の列（印・順位・人気 …）と ``RESULT_COLUMNS``。
        """
        table = predictions[["race_id", "race_date", "horse_id", "probability", "fold"]].merge(
            places, on=["race_id", "horse_id"], how="inner")
        table["place_value"] = self._place_value(table)
        table = table.merge(dangers.drop(columns=["horse_no"], errors="ignore"), on=["race_id", "horse_id"], how="left")
        table = table.rename(columns={TOP3_RATE: "market_top3"})
        table["is_danger"] = table["is_danger"].astype("boolean").fillna(False).astype(bool)
        marked = [self._mark_race(race) for _, race in table.groupby("race_id", sort=False)]
        return pd.concat(marked, ignore_index=True)

    def _mark_race(self, race: pd.DataFrame) -> pd.DataFrame:
        marked = self._marks.assign(race.drop(columns=["popularity"]))
        known = race.set_index("horse_no")
        for column in RESULT_COLUMNS:
            marked[column] = known.loc[marked["horse_no"], column].to_numpy()
        return marked

    def _place_value(self, table: pd.DataFrame) -> pd.Series:
        """複勝の期待値（3着以内の確率 × 見込みの払戻の倍率）。見込みの倍率が無ければ欠損値。"""
        if self._estimator is None:
            return pd.Series(float("nan"), index=table.index)
        market = pd.DataFrame({
            FIELD_SIZE: table["field_size"], PLACE_ODDS_LOW: table["place_odds_low"], PLACE_ODDS_HIGH: table["place_odds_high"],
            TOP2_RATE: table[TOP2_RATE], TOP3_RATE: table[TOP3_RATE],
        })
        return PlaceExpectedValue(self._estimator).of(table["probability"], market)[PLACE_VALUE]
