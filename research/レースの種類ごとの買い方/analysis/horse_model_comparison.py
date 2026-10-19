"""上のクラス・ハンデ戦のレースのテスト期間で、学び直した馬の予想モデルどうしの確率の誤差（対数損失）を比べる。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

#: 採用の基準（docs/01 の 7）: 比べる相手より誤差が小さい区切りの数がこの割合以上で、全部を合わせても小さいこと。
WIN_SHARE = 0.7
#: 確率の端を丸める幅（対数が −∞ にならないように）。
_CLIP = 1e-6


class HorseModelComparison:
    """予測の表（``WalkForwardRunner`` の表。列 区切り・期間・レースID・馬番・確率）を、正解の表（列 レースID・馬番・``label``・``segment``）と
    突き合わせ、テスト期間の ``segment`` が真の行について、区切りごとの対数損失を出す。``base`` が比べる相手の名前。"""

    def __init__(self, labels: pd.DataFrame, label: str, segment: str) -> None:
        self._labels = labels[["レースID", "馬番", label, segment]].rename(columns={label: "y", segment: "target"})

    def table(self, predictions: Mapping[str, pd.DataFrame], base: str) -> pd.DataFrame:
        losses = {name: self._losses(frame) for name, frame in predictions.items()}
        table = pd.DataFrame({name: values["loss"] for name, values in losses.items()})
        table.insert(0, "行", losses[base]["rows"])
        return table

    def verdict(self, table: pd.DataFrame, candidate: str, base: str) -> tuple[int, int, bool]:
        """（比べる相手より誤差が小さい区切りの数, 区切りの数, 採用の基準を満たすか）。全部を合わせた誤差は行数で重みを付けた平均。"""
        wins = int((table[candidate] < table[base]).sum())
        total = (table[candidate] * table["行"]).sum() < (table[base] * table["行"]).sum()
        return wins, len(table), bool(wins >= WIN_SHARE * len(table) and total)

    def _losses(self, frame: pd.DataFrame) -> pd.DataFrame:
        test = frame[frame["期間"] == "テスト"][["区切り", "レースID", "馬番", "確率"]]
        joined = test.assign(レースID=test["レースID"].astype(str)).merge(
            self._labels.assign(レースID=self._labels["レースID"].astype(str)), on=["レースID", "馬番"], how="inner")
        joined = joined[joined["target"].astype(bool)]
        p = joined["確率"].clip(_CLIP, 1 - _CLIP)
        y = joined["y"].astype(float)
        joined = joined.assign(loss=-(y * np.log(p) + (1 - y) * np.log(1 - p)))
        return joined.groupby("区切り", sort=False).agg(rows=("loss", "size"), loss=("loss", "mean"))
