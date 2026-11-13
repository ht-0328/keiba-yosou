"""区切りごとの1着の予測の当たり具合（参考）: レースの中のログ損失と、確率の帯ごとの実際の勝率。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import MarketWinProbability

from 印の成績.win5_fold_predictions import Win5FoldPredictions
from 印の成績.win5_periods import EXPLORE_START

#: 確率の帯の区切り（そろえた1着の確率）。
BAND_EDGES: tuple[float, ...] = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 1.0)
#: 比べる確率の名前。
_SHARE = "そろえた1着の確率"
_RAW = "そろえる前の確率（2つのモデルの平均のまま）"
_MARKET = "オッズから見た勝率"
#: 範囲の名前。
ALL_RACES = "全レース"
TARGET_RACES = "WIN5 の対象レースだけ"


class Win5ProbabilityReport:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 2. の「1着の確率（参考）」。2019年からのテスト期間の当日・前日の区切りごとの予測で、
    全レースと WIN5 の対象レースだけについて、(1) 勝ち馬に付けた確率の対数の平均に −1 を掛けたもの（レースの中のログ損失。そろえた確率・
    そろえる前の確率・オッズから見た勝率）と、(2) そろえた確率の帯ごとの平均の確率と実際の勝率を出す。採用の基準には使わない。"""

    def __init__(self) -> None:
        self._market = MarketWinProbability()

    def tables(self, predictions: Win5FoldPredictions, results: pd.DataFrame, target_race_ids: set[str]) -> list[Table]:
        """``results`` は ``RaceResults`` の表（列 race_id・horse_no・finish・win_odds）。"""
        losses, bands = [], []
        for timing, tested in ((PredictionTiming.RACE_DAY, predictions.race_day), (PredictionTiming.DAY_BEFORE, predictions.day_before)):
            joined = self._joined(tested, results)
            for scope, frame in ((ALL_RACES, joined), (TARGET_RACES, joined.loc[joined["race_id"].isin(target_race_ids)])):
                losses.append([timing.label, scope, *self._losses(frame)])
                bands.extend([timing.label, scope, *row] for row in self._bands(frame))
        loss_table = Table(["時点", "範囲", "レース数", f"ログ損失（{_SHARE}）", f"ログ損失（{_RAW}）", f"ログ損失（{_MARKET}）"], losses,
                           title="WIN5 の参考: 1着の確率のレースの中のログ損失（2019年からのテスト期間）",
                           note="勝ち馬に付けた確率の対数の平均に −1 を掛けたもの。小さいほど勝ち馬に高い確率を付けている。採用の基準には使わない。")
        band_table = Table(["時点", "範囲", "そろえた1着の確率の帯", "頭数", "平均の確率", "実際の勝率"], bands,
                           title="WIN5 の参考: そろえた1着の確率の帯ごとの実際の勝率（2019年からのテスト期間）",
                           note="組の確率は5頭のかけ算なので、確率の小さい帯で平均の確率が実際の勝率より大きいと、穴の組を見積もりすぎる。")
        return [loss_table, band_table]

    def _joined(self, tested: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
        """出走した馬だけの予測に、着順・確定の単勝オッズと、そろえた確率・オッズから見た勝率を足した表（勝ち馬のいるレースだけ）。"""
        recent = tested.loc[tested["race_date"] >= EXPLORE_START, ["race_id", "horse_no", "probability"]]
        joined = recent.merge(results[["race_id", "horse_no", "finish", "win_odds"]], on=["race_id", "horse_no"], how="inner")
        joined = joined.loc[joined["probability"] > 0].copy()
        joined["share"] = joined["probability"] / joined.groupby("race_id")["probability"].transform("sum")
        joined["market"] = self._market.of(joined["race_id"], joined["win_odds"])
        joined["won"] = pd.to_numeric(joined["finish"], errors="coerce") == 1
        has_winner = joined.groupby("race_id")["won"].transform("any")
        return joined.loc[has_winner].reset_index(drop=True)

    def _losses(self, frame: pd.DataFrame) -> list[object]:
        winners = frame.loc[frame["won"]]
        values = [self._loss(winners[column]) for column in ("share", "probability", "market")]
        return [int(frame["race_id"].nunique()), *values]

    def _loss(self, values: pd.Series) -> str:
        usable = values.loc[values > 0]
        return f"{-float(np.log(usable).mean()):.4f}" if not usable.empty else ""

    def _bands(self, frame: pd.DataFrame) -> list[list[object]]:
        cut = pd.cut(frame["share"], bins=list(BAND_EDGES), include_lowest=True, right=False)
        rows = []
        for band, group in frame.groupby(cut, observed=True, sort=True):
            rows.append([f"{band.left:.0%}〜{band.right:.0%}", len(group), f"{group['share'].mean():.2%}", f"{group['won'].mean():.2%}"])
        return rows
