"""配当の見積もりの確かめ: 区切りごとの式と、確認期間の当たり組での見積もりと実際の払戻の比べ。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.payout import (
    ComboMarketProbability,
    PayoutCeiling,
    PayoutEstimator,
    PayoutFeatures,
    PayoutPool,
    PoolSizeEstimate,
)
from yosou.form_aptitude_win5_tickets.repository.win5_columns import (
    CARRY,
    INVERSE_SUMS,
    NO_HIT,
    PAYOUT,
    RACE_DATE,
    SATURDAY,
    WINNER_ODDS,
)

from 印の成績.win5_periods import CONFIRM_START, EXPLORE_START

#: 見積もりの配当の帯の区切り（100円あたりの円）。
BAND_EDGES: tuple[float, ...] = (0.0, 1e4, 1e5, 1e6, 1e7, 1e8, float("inf"))
_BAND_NAMES: tuple[str, ...] = ("1万円未満", "1万〜10万円", "10万〜100万円", "100万〜1000万円", "1000万〜1億円", "1億円以上")


class Win5PayoutReport:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 8.。区切りごとに作った配当の見積もりの式（傾き・切片・外れの散らばり）と、
    確認期間の当たり組について、その日の区切りの式で見積もった配当と実際の払戻の比べ（外れ = log(実際) − log(見積もり) の平均と散らばり、
    見積もりの帯ごとの平均）、的中無の回の当たり組の見積もりの配当が払戻に回るお金の何割に出ていたかを出す。

    見積もりは予想と同じ部品（``ComboMarketProbability``・``PayoutFeatures``・``PayoutEstimator``・``PayoutCeiling``）で、発売票数はその日より前の回から見積もる。
    """

    def __init__(self) -> None:
        self._pool_size = PoolSizeEstimate()
        self._market = ComboMarketProbability()
        self._features = PayoutFeatures()
        self._ceiling = PayoutCeiling()

    def tables(self, history: pd.DataFrame, estimators: dict[str, PayoutEstimator], folds: pd.DataFrame) -> list[Table]:
        """``folds`` の列は fold・start。確認期間の日は、テスト期間の始まりがその日以前でいちばん新しい区切りの式で見積もる。"""
        ordered = folds.sort_values("start")
        estimated = self._estimated(history, estimators, ordered)
        hits = estimated.loc[~estimated[NO_HIT] & (estimated[PAYOUT] > 0)]
        misses = estimated.loc[estimated[NO_HIT]]
        return [self._formulas(estimators, ordered), self._errors(hits), self._bands(hits), self._no_hits(misses)]

    def _estimated(self, history: pd.DataFrame, estimators: dict[str, PayoutEstimator], folds: pd.DataFrame) -> pd.DataFrame:
        """確認期間の当たり組ごとの、見積もりの配当と払戻に回るお金の見込み。"""
        rows = history.loc[history[RACE_DATE] >= CONFIRM_START].copy()
        rows["market"] = self._market.of_winners(rows[WINNER_ODDS], rows[INVERSE_SUMS])
        rows = rows.loc[rows["market"].notna()]
        estimates, money = [], []
        for _, row in rows.iterrows():
            fold = folds.loc[folds["start"] <= row[RACE_DATE], "fold"].iloc[-1]
            pool = PayoutPool(self._pool_size.of(history, date.fromisoformat(row[RACE_DATE]), bool(row[SATURDAY])), int(row[CARRY]))
            features = self._features.of(np.array([row["market"]]), pool.carry, pool.votes)
            estimates.append(float(self._ceiling.apply(estimators[str(fold)].estimate(features), pool.money)[0]))
            money.append(pool.money)
        return rows.assign(estimate=estimates, money=money, **{NO_HIT: rows[NO_HIT].astype(bool)})

    def _formulas(self, estimators: dict[str, PayoutEstimator], folds: pd.DataFrame) -> Table:
        rows = []
        for fold, start in zip(folds["fold"], folds["start"], strict=True):
            if start < EXPLORE_START:
                continue
            each = estimators[str(fold)]
            rows.append([fold, start, each.count, f"{each.slopes[0]:.3f}", f"{each.slopes[1]:.3f}", f"{each.intercept:.3f}",
                         f"{each.residual_std:.3f}"])
        return Table(["区切り", "テスト期間の始まり", "使った当たり組", "傾き1（市場の組の確率の逆数の対数）", "傾き2（キャリーオーバーの比の対数）",
                      "切片", "外れの散らばり"], rows, title="WIN5 の配当の見積もりの式（区切りごと）",
                     note="区切りごとに、テスト期間の始まりより前の WIN5 の当たり組だけで作った式。傾き1 が 1 から大きく離れたり区切りで大きく変われば、式が安定していない。")

    def _errors(self, hits: pd.DataFrame) -> Table:
        error = np.log(hits[PAYOUT].astype(float)) - np.log(hits["estimate"])
        row = [len(hits), f"{error.mean():+.3f}", f"{error.std():.3f}", f"{np.exp(error.mean()):.2f}倍"] if len(hits) else [0, "", "", ""]
        return Table(["当たり組", "外れの平均", "外れの散らばり", "実際 ÷ 見積もり（平均の外れから）"], [row],
                     title="WIN5 の配当の見積もりの外れ（確認期間の当たり組）",
                     note="外れ = log(実際の払戻) − log(見積もりの配当)。平均が 0 より小さいと、式が配当を高く見ている（買わなくてよい日を買うことになる）。")

    def _bands(self, hits: pd.DataFrame) -> Table:
        cut = pd.cut(hits["estimate"], bins=list(BAND_EDGES), labels=list(_BAND_NAMES), right=False)
        rows = []
        for band, group in hits.groupby(cut, observed=True, sort=True):
            error = np.log(group[PAYOUT].astype(float)) - np.log(group["estimate"])
            rows.append([band, len(group), f"{group['estimate'].mean():,.0f}", f"{group[PAYOUT].mean():,.0f}", f"{error.mean():+.3f}"])
        return Table(["見積もりの配当の帯", "当たり組", "見積もりの平均（円）", "実際の平均（円）", "外れの平均"], rows,
                     title="WIN5 の見積もりの配当の帯ごとの比べ（確認期間の当たり組）",
                     note="人気薄の組（見積もりの大きい帯）で、見積もりが実際より大きく出ていないかを見る。")

    def _no_hits(self, misses: pd.DataFrame) -> Table:
        rows = [[row[RACE_DATE], f"{row['estimate']:,.0f}", f"{row['estimate'] / row['money']:.1%}"] for _, row in misses.iterrows()]
        return Table(["開催日", "当たり組の見積もりの配当（円）", "払戻に回るお金に対する割合"], rows,
                     title="WIN5 の的中無の回の見積もり（確認期間）",
                     note="当たる人がいない組を、払戻に回るお金の近くまで大きく見積もれているか（割合が大きいほど、そう見ている）。")
