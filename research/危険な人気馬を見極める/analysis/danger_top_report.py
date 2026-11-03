"""危険度の高い人気馬だけを取り出して、同じ人気の馬全体と成績・回収率を比べる表。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from 共通.render import Table

from .calibrated_window_trainer import ODDS_ONLY_COLUMN

#: 予測の表の列（研究「既存モデルの改善」の walk_forward が書く名前）。
_KEYS = ["レースID", "馬ID"]
_PROBABILITY, _PART, _SEGMENT = "確率", "期間", "区分"
_TEST = "テスト"
#: 学習データの評価用の列。
_FINISH, _POPULARITY, _WIN_PAYOUT, _PLACE_PAYOUT, _TOP3_RATE = (
    "確定着順", "確定の単勝人気", "単勝の払戻", "複勝の払戻", "オッズから見た3着以内率")
#: 取り出す危険度の上位の割合。
SHARES: tuple[float, ...] = (0.05, 0.10, 0.20)
_BANDS: tuple[str, ...] = ("1番人気", "2〜3番人気", "4〜5番人気")


class DangerTopReport:
    """作り方ごとに、テスト期間の人気帯ごとの「危険度の上位 x%」の馬の成績を、同じ人気の馬全体と比べる。

    危険度 = 予想の4着以下の確率 − 比べる相手。比べる相手は、予測の表にオッズだけのモデルの確率（``ODDS_ONLY_COLUMN``）が
    あればそれ、無ければ今の本番と同じオッズから計算した4着以下の確率（1 − オッズから見た3着以内率）。
    「同じ人気の馬全体」は、取り出した馬と同じ人気の馬全体の成績を、人気の内訳で重み付けした平均（人気どおりに同じ頭数を買った場合）。
    危険度が本当に効いていれば、上位の馬ほど3着以内率と回収率が同じ人気の馬全体より低い。
    """

    def table(self, evaluation: pd.DataFrame, predictions: Mapping[str, pd.DataFrame]) -> Table:
        """``evaluation`` は学習データの ID と評価用の列を並べた表、``predictions`` は 作り方の名前 → 予測の表。"""
        rows = []
        for name, frame in predictions.items():
            scored = self._scored(evaluation, frame)
            base = self._base(scored)
            for band in _BANDS:
                group = scored[scored[_SEGMENT] == band]
                for share in SHARES:
                    rows.append([name, band, f"上位{share:.0%}", *self._row(group, share, base)])
        return Table(["作り方", "人気帯", "危険度", "頭数", "3着以内率", "同じ人気の馬全体", "差", "単勝回収率", "同じ人気の馬全体",
                      "複勝回収率", "同じ人気の馬全体"], rows, title="危険度の上位の人気馬の成績（テスト期間）")

    def _scored(self, evaluation: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
        test = frame[frame[_PART] == _TEST]
        merged = test.merge(evaluation, on=_KEYS, how="inner")
        standard = merged[ODDS_ONLY_COLUMN] if ODDS_ONLY_COLUMN in merged.columns else 1 - merged[_TOP3_RATE]
        return merged.assign(danger=merged[_PROBABILITY] - standard, top3=(merged[_FINISH] <= 3).astype(float))

    def _base(self, scored: pd.DataFrame) -> pd.DataFrame:
        """人気ごとの、テスト期間の全体の成績。"""
        return scored.groupby(_POPULARITY).agg(top3=("top3", "mean"), win=(_WIN_PAYOUT, "mean"), place=(_PLACE_PAYOUT, "mean"))

    def _row(self, group: pd.DataFrame, share: float, base: pd.DataFrame) -> list[object]:
        picked = group[group["danger"] >= group["danger"].quantile(1 - share)]
        expected = base.reindex(picked[_POPULARITY]).mean()
        top3 = picked["top3"].mean()
        return [f"{len(picked):,}", f"{top3:.1%}", f"{expected['top3']:.1%}", f"{(top3 - expected['top3']) * 100:+.1f}",
                f"{picked[_WIN_PAYOUT].mean():.1f}%", f"{expected['win']:.1f}%",
                f"{picked[_PLACE_PAYOUT].mean():.1f}%", f"{expected['place']:.1f}%"]
