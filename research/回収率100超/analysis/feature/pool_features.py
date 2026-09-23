"""券種プールごとの確率を、モデルに渡せる列に変える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 単勝オッズから作った勝率と比べる列（どの券種プールが、単勝と食い違っているか）。
_WIN_LIKE = ("3連単から見た勝率", "馬単から見た勝率", "単勝票数の配分")
#: 単勝オッズから作った複勝率と比べる列。
_PLACE_LIKE = ("3連複から見た3着以内率", "ワイドから見た3着以内率", "複勝から見た3着以内率",
               "馬連から見た2着以内率", "複勝票数の配分")


class PoolFeatures:
    """プールごとの確率から、log・レース内順位・単勝との食い違いの3種類の列を作る。

    そのままの確率をモデルに渡すと、0.001 と 0.002 の違い（人気薄どうしの倍の差）が
    0.30 と 0.301 の違いと同じ大きさに見えてしまう。log にすると、どちらも「倍か、わずかか」で測れる。

    レース内順位は「このレースの中で何番目に支持されているか」で、頭数が違っても同じ意味になる。

    食い違いは「大きなプールが、単勝オッズより高く（低く）見ている度合い」で、この研究がいちばん使う列である。
    売上の大きい 3連単・3連複のほうが情報が多いなら、この差は「単勝が間違っている向き」を指している。
    """

    def __init__(self, pool_columns: tuple[str, ...], win_baseline: str, place_baseline: str) -> None:
        self._pool_columns = pool_columns
        self._win_baseline = win_baseline
        self._place_baseline = place_baseline

    def add_to(self, frame: pd.DataFrame, race_column: str = "rid") -> tuple[pd.DataFrame, list[str]]:
        """``frame`` に列を足して、（表, 足した列名）を返す。"""
        added: list[str] = []
        race = frame[race_column]
        for column in (*self._pool_columns, self._win_baseline, self._place_baseline):
            frame[f"log_{column}"] = np.log(np.clip(frame[column], 1e-9, None))
            frame[f"順位_{column}"] = frame[column].groupby(race).rank(ascending=False, method="min")
            added += [f"log_{column}", f"順位_{column}"]
        added += self._add_gaps(frame)
        return frame, added

    def _add_gaps(self, frame: pd.DataFrame) -> list[str]:
        """単勝オッズから作った確率との食い違い。"""
        added: list[str] = []
        for column in self._pool_columns:
            baseline = self._win_baseline if column in _WIN_LIKE else self._place_baseline
            name = f"{column}と単勝の差"
            frame[name] = frame[f"log_{column}"] - frame[f"log_{baseline}"]
            added.append(name)
        return added
