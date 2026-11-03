"""来そうと見た穴馬だけを取り出して、同じ人気の馬全体と成績・回収率を比べる表。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from 共通.render import Table

from .calibrated_window_trainer import ODDS_ONLY_COLUMN

#: 予測の表の列（研究「既存モデルの改善」の walk_forward が書く名前）。
_KEYS = ["レースID", "馬ID"]
_PROBABILITY, _PART = "確率", "期間"
_TEST = "テスト"
#: 学習データ（穴馬の予想の表）の評価用の列。
_FINISH, _POPULARITY, _WIN_PAYOUT, _PLACE_PAYOUT, _ZONE = (
    "確定着順", "確定の単勝人気", "単勝の払戻", "複勝の払戻", "穴馬の区分")
#: 特徴量の、オッズから計算した3着以内率（Harville の式）。比べる相手の無い予測の表で使う。
_TOP3_RATE = "オッズから見た3着以内率"
#: 取り出す穴馬度の上位の割合。
SHARES: tuple[float, ...] = (0.05, 0.10, 0.20)
_ZONES: tuple[str, ...] = ("中穴", "大穴")


class LongshotTopReport:
    """作り方ごとに、テスト期間の区分（中穴・大穴）ごとの「穴馬度の上位 x%」の馬の成績を、同じ人気の馬全体と比べる。

    穴馬度 = 予想の3着以内の確率 − 比べる相手。比べる相手は、予測の表にオッズだけのモデルの確率（``ODDS_ONLY_COLUMN``）が
    あればそれ、無ければオッズから計算した3着以内率。穴馬（人気馬の範囲より下の人気）の行だけを見る。
    全頭の予想の予測を渡してもよい（穴馬の行だけを取り出し、区分は評価用の列から付ける）。
    穴馬度が本当に効いていれば、上位の馬ほど3着以内率と複勝の回収率が同じ人気の馬全体より高い。
    """

    def table(self, evaluation: pd.DataFrame, predictions: Mapping[str, pd.DataFrame]) -> Table:
        """``evaluation`` は穴馬の予想の学習データの ID・評価用の列・オッズから見た3着以内率を並べた表、
        ``predictions`` は 作り方の名前 → 予測の表。"""
        rows = []
        for name, frame in predictions.items():
            scored = self._scored(evaluation, frame)
            base = self._base(scored)
            for zone in _ZONES:
                group = scored[scored[_ZONE] == zone]
                for share in SHARES:
                    rows.append([name, zone, f"上位{share:.0%}", *self._row(group, share, base)])
        return Table(["作り方", "区分", "穴馬度", "頭数", "3着以内率", "同じ人気の馬全体", "差", "単勝回収率", "同じ人気の馬全体",
                      "複勝回収率", "同じ人気の馬全体"], rows, title="穴馬度の上位の穴馬の成績（テスト期間）")

    def _scored(self, evaluation: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
        test = frame[frame[_PART] == _TEST].drop(columns=[_ZONE, _TOP3_RATE], errors="ignore")
        merged = test.merge(evaluation[evaluation[_ZONE].notna()], on=_KEYS, how="inner")
        standard = merged[ODDS_ONLY_COLUMN] if ODDS_ONLY_COLUMN in merged.columns else merged[_TOP3_RATE]
        return merged.assign(value=merged[_PROBABILITY] - standard, top3=(merged[_FINISH] <= 3).astype(float))

    def _base(self, scored: pd.DataFrame) -> pd.DataFrame:
        """人気ごとの、テスト期間の全体の成績。"""
        return scored.groupby(_POPULARITY).agg(top3=("top3", "mean"), win=(_WIN_PAYOUT, "mean"), place=(_PLACE_PAYOUT, "mean"))

    def _row(self, group: pd.DataFrame, share: float, base: pd.DataFrame) -> list[object]:
        picked = group[group["value"] >= group["value"].quantile(1 - share)]
        expected = base.reindex(picked[_POPULARITY]).mean()
        top3 = picked["top3"].mean()
        return [f"{len(picked):,}", f"{top3:.1%}", f"{expected['top3']:.1%}", f"{(top3 - expected['top3']) * 100:+.1f}",
                f"{picked[_WIN_PAYOUT].mean():.1f}%", f"{expected['win']:.1f}%",
                f"{picked[_PLACE_PAYOUT].mean():.1f}%", f"{expected['place']:.1f}%"]
