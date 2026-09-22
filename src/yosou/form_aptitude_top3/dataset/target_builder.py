"""目的変数を付ける。"""

from __future__ import annotations

import pandas as pd

from .column_names import TOP3, WIN

#: 3着以内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE = 3


class TargetBuilder:
    """目的変数（設計書 10）。確定着順で決める。``TargetLabeler`` を守る。

    - 3着以内: 確定着順が 1〜3 なら 1。4着以下と、着順の付かない競走中止・失格は 0。
    - 1着: 確定着順が 1 なら 1。
    - 同着は、どちらも同じ着順として扱う（3着同着なら 2頭とも 1）。
    """

    @property
    def label_name(self) -> str:
        """モデルに当てさせる列の名前。この予想は「3着以内」（「1着」は単勝用に置いておくだけ）。"""
        return TOP3

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``samples`` と同じ。"""
        # 着順なしは NaN にする（DuckDB の整数の欠損値 <NA> のままだと、比べた結果も欠損値になる）
        finish = pd.to_numeric(samples["finish"], errors="coerce").astype("float64")
        return pd.DataFrame({
            TOP3: finish.between(1, _LAST_PLACE).astype(int),
            WIN: (finish == 1).astype(int),
        }, index=samples.index)
