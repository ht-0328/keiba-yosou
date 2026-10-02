"""予測するレースの券種のオッズがそろっているかを確かめる。"""

from __future__ import annotations

from yosou.shared.dataset import PredictionData

from ..feature import POOL_SUPPORT_NAMES


class PoolAvailability:
    """予測用データの N（券種ごとのオッズから見た支持）の6列のうち、どれか1列でも全部の馬で欠損値なら「券種のオッズが無い」とする。

    まだ速報の全券種のオッズ（0B30）を取り込んでいないレースや、取り込んだ券種が足りないレースなど。学習データでは、
    券種のオッズが丸ごと無いレースはほとんど無いので、欠けたまま N を使うモデルに渡すと、学習のときと違う様子のデータに
    なる。そのときは N を使わないモデルで予測する。N を使わない時点（木曜・前日）の予測用データは、常に「ある」とする。
    """

    def missing(self, data: PredictionData) -> bool:
        columns = [name for name in POOL_SUPPORT_NAMES if name in data.features.columns]
        return bool(columns) and bool(data.features[columns].isna().all().any())
