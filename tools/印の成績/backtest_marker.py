"""終わったレースの予測に、今週の予想と同じ決め方で印を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_HIGH, PLACE_ODDS_LOW
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE, WIN_RATE, MarketPlaces
from yosou.shared.place_value import PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.win_value import LINE, ExpectationLevel

from 今週の予想.forecast_columns import EXPECTATION, MARK, MARKET_TOP3, MARKET_WIN, PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK, MarkRule

from 印の成績.filter_columns import (
    AGREEMENT,
    MEMBERS,
    ODDS_EVENING,
    ODDS_MORNING,
    ODDS_MOVE,
    POOL_BACKED,
    POOL_SUPPORT,
    POOL_SUPPORT_LINE,
    POOL_WIN,
    member_column,
    member_columns,
)

#: 印を付けた表に残す、結果の列。
RESULT_COLUMNS: tuple[str, ...] = ("finish", "popularity", "win_odds", "win_payout", "place_payout", "fold")
#: 予測から写す列（モデルごとの確率は、あれば写す）。
_PREDICTION_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "horse_id", PROBABILITY, "fold")
#: オッズの無い時点（木曜）で空にする、オッズから出す列。
_ODDS_COLUMNS: tuple[str, ...] = (
    "win_odds", MARKET_TOP3, MARKET_WIN, "place_value", WIN_VALUE, *member_columns("place_value"), *member_columns(WIN_VALUE),
    POOL_WIN, POOL_SUPPORT, ODDS_EVENING, ODDS_MORNING, ODDS_MOVE,
)


class BacktestMarker:
    """全頭の予想の予測（3着以内に入る確率）と、1着の予想の予測（1着になる確率と単勝の期待値）、レースの結果・確定オッズ・危険な人気馬の判定から、
    レースごとに ◎○▲△☆注消 とレースの期待度を付ける。

    市場の見立て（オッズから見た勝率・3着以内率）と複勝の期待値は、今週の予想と同じ部品で、確定オッズから出す。
    ``estimator`` は複勝の見込みの倍率（全頭の予想の学習済みモデルと一緒に保存した ``place_price.json``）。無ければ期待値は出さず、☆ は付かない。
    期待度は、◎ の単勝の期待値から ``ExpectationLevel``（線は 1.00 で固定）で決める。
    ``odds_known`` を偽にすると（木曜の予測）、本番の木曜と同じく、オッズから出すもの（市場の見立て・複勝の期待値・単勝の期待値・危険な人気馬）を
    使わずに印を付ける（◎ は1着になる確率の1位、☆・注・期待度は付かない）。成績の人気・払戻は確定の値のまま。

    絞り込みの旗（研究「回収率100超の施策」）も、レースの全頭に付ける。
    - ``agreement``（2モデル一致）: ◎ の単勝の期待値が、LightGBM と CatBoost のそれぞれの確率でも線以上。モデルごとの確率が無ければ偽。
    - ``pool_backed``（3連単の支持あり）: ◎ の「3連単から見た勝率 ÷ 単勝から見た勝率」（``pool_support``）が線以上。3連単の確率が無ければ偽。
    馬ごとに、モデルごとの3着以内の確率・複勝の期待値（``probability_lightgbm``・``place_value_lightgbm`` など）も残す。
    """

    def __init__(self, estimator: PlacePriceEstimator | None, odds_known: bool = True) -> None:
        self._estimator = estimator
        self._odds_known = odds_known
        self._marks = MarkRule()
        self._expectation = ExpectationLevel()

    def places(self, results: pd.DataFrame) -> pd.DataFrame:
        """出走の行に、オッズから見た勝率・2着以内率・3着以内率を付ける（レースの全頭で出す）。"""
        return pd.concat([results, MarketPlaces().of(results[["race_id", "win_odds"]]).set_axis(results.index)], axis=1)

    def mark(self, predictions: pd.DataFrame, places: pd.DataFrame, dangers: pd.DataFrame,
             wins: pd.DataFrame | None = None, pools: pd.DataFrame | None = None,
             movements: pd.DataFrame | None = None) -> pd.DataFrame:
        """``predictions`` はテスト期間の全頭の予想の行、``places`` は ``places`` の戻り値、``dangers`` は危険な人気馬の判定、
        ``wins`` は1着の予想のテスト期間の行（``WinValueAttacher.attach``。無ければ ◎ は3着以内の確率の1位で、期待度は付かない）、
        ``pools`` は3連単から見た勝率（``PoolWinReader.read``。列 race_id・horse_no・pool_win。無ければ 3連単の支持は見ない）、
        ``movements`` は前日夜 → 当日朝の単勝オッズ（``OddsSnapshotRepository.read``。列 race_id・horse_no・odds_evening・odds_morning。無ければ空）。

        戻り値は1行 = 1頭。列は race_id・race_date と ``MarkRule.assign`` の列（印・順位・人気 …）と、レースの期待度・絞り込みの旗、``RESULT_COLUMNS``。
        """
        columns = [*_PREDICTION_COLUMNS, *(column for column in member_columns(PROBABILITY) if column in predictions.columns)]
        table = predictions[columns].merge(places, on=["race_id", "horse_id"], how="inner")
        table["place_value"] = self._place_value(table, PROBABILITY)
        for member in MEMBERS:
            source = member_column(PROBABILITY, member)
            if source in table.columns:
                table[member_column("place_value", member)] = self._place_value(table, source)
        table = table.merge(dangers.drop(columns=["horse_no"], errors="ignore"), on=["race_id", "horse_id"], how="left")
        if wins is not None:
            table = table.merge(wins, on=["race_id", "horse_id"], how="left")
        table = table.rename(columns={TOP3_RATE: MARKET_TOP3, WIN_RATE: MARKET_WIN})
        table = self._with_pools(table, pools)
        table = self._with_movements(table, movements)
        table["is_danger"] = table["is_danger"].astype("boolean").fillna(False).astype(bool)
        marked = [self._mark_race(race) for _, race in table.groupby("race_id", sort=False)]
        return pd.concat(marked, ignore_index=True)

    def _with_pools(self, table: pd.DataFrame, pools: pd.DataFrame | None) -> pd.DataFrame:
        """3連単から見た勝率と、単勝から見た勝率との比を付ける。無ければ欠損値。"""
        if pools is None or pools.empty:
            return table.assign(**{POOL_WIN: np.nan, POOL_SUPPORT: np.nan})
        keyed = pools[["race_id", "horse_no", POOL_WIN]].astype({"race_id": str, "horse_no": int}).drop_duplicates(["race_id", "horse_no"])
        merged = table.assign(horse_no=table["horse_no"].astype(int)).merge(keyed, on=["race_id", "horse_no"], how="left")
        market = merged[MARKET_WIN].astype(float)
        merged[POOL_SUPPORT] = merged[POOL_WIN].astype(float) / market.where(market > 0)
        return merged

    def _with_movements(self, table: pd.DataFrame, movements: pd.DataFrame | None) -> pd.DataFrame:
        """前日夜と当日朝の単勝オッズと、その動き（log(当日朝 ÷ 前日夜)。負なら売れた）を付ける。無ければ欠損値。"""
        if movements is None or movements.empty:
            return table.assign(**{ODDS_EVENING: np.nan, ODDS_MORNING: np.nan, ODDS_MOVE: np.nan})
        keyed = movements[["race_id", "horse_no", ODDS_EVENING, ODDS_MORNING]].astype({"race_id": str, "horse_no": int})
        merged = table.assign(horse_no=table["horse_no"].astype(int)).merge(keyed.drop_duplicates(["race_id", "horse_no"]),
                                                                              on=["race_id", "horse_no"], how="left")
        evening, morning = merged[ODDS_EVENING].astype(float), merged[ODDS_MORNING].astype(float)
        merged[ODDS_MOVE] = np.log(morning.where(morning > 0)) - np.log(evening.where(evening > 0))
        return merged

    def _mark_race(self, race: pd.DataFrame) -> pd.DataFrame:
        marked = self._marks.assign(self._for_marks(race))
        known = race.set_index("horse_no")
        for column in RESULT_COLUMNS:
            marked[column] = known.loc[marked["horse_no"], column].to_numpy()
        top = marked.index[marked[MARK] == TOP_MARK]
        value = float(marked.loc[top[0], WIN_VALUE]) if len(top) else float("nan")
        marked[EXPECTATION] = self._expectation.of(value)
        marked[AGREEMENT] = self._agreement(marked, top)
        marked[POOL_BACKED] = self._pool_backed(marked, top)
        return marked

    def _agreement(self, marked: pd.DataFrame, top: pd.Index) -> bool:
        """◎ の単勝の期待値が、2つのモデルのそれぞれの確率でも線以上か。"""
        if not len(top):
            return False
        values = [marked.loc[top[0], column] for column in member_columns(WIN_VALUE) if column in marked.columns]
        return len(values) == len(MEMBERS) and all(pd.notna(value) and float(value) >= LINE for value in values)

    def _pool_backed(self, marked: pd.DataFrame, top: pd.Index) -> bool:
        """◎ の「3連単から見た勝率 ÷ 単勝から見た勝率」が線以上か。"""
        if not len(top):
            return False
        support = marked.loc[top[0], POOL_SUPPORT]
        return bool(pd.notna(support) and float(support) >= POOL_SUPPORT_LINE)

    def _for_marks(self, race: pd.DataFrame) -> pd.DataFrame:
        """印を付けるのに渡す表。オッズの無い時点（木曜）は、オッズから出す列を空にする（本番の木曜の予測と同じ形）。"""
        table = race.drop(columns=["popularity"])
        if self._odds_known:
            return table
        blank = {column: np.nan for column in _ODDS_COLUMNS if column in table.columns}
        return table.assign(**blank, is_danger=False)

    def _place_value(self, table: pd.DataFrame, probability: str) -> pd.Series:
        """複勝の期待値（3着以内の確率 × 見込みの払戻の倍率）。見込みの倍率が無ければ欠損値。"""
        if self._estimator is None:
            return pd.Series(float("nan"), index=table.index)
        market = pd.DataFrame({
            FIELD_SIZE: table["field_size"], PLACE_ODDS_LOW: table["place_odds_low"], PLACE_ODDS_HIGH: table["place_odds_high"],
            TOP2_RATE: table[TOP2_RATE], TOP3_RATE: table[TOP3_RATE],
        })
        return PlaceExpectedValue(self._estimator).of(table[probability], market)[PLACE_VALUE]
