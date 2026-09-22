"""目的変数（3着以内）を付ける。"""

from __future__ import annotations

import pandas as pd

from ..feature import as_numbers

#: 目的変数の列の名前。モデルに当てさせるのは「3着以内」で、「1着」は単勝用のモデルのために置いておく。
TOP3 = "3着以内"
WIN = "1着"
#: 3着以内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE = 3


class Top3TargetBuilder:
    """目的変数「3着以内なら 1」（手本の設計書 10・穴馬の設計書 10）。確定着順で決める。``TargetLabeler`` を守る。

    近走と適性の予想（``form_aptitude_top3``）と穴馬の予想（``longshots_in_top3``）が、そのまま使う。

    - 3着以内: 確定着順が 1〜3 なら 1。4着以下と、着順の付かない競走中止・失格は 0。
    - 1着: 確定着順が 1 なら 1。モデルには渡さず、単勝用のモデルを作るときのために置いておく。
    - 出走しなかった馬（取消・除外）は、行を選ぶクラスがすでに除いている。
    - 同着は、どちらも同じ着順として扱う（3着同着なら 2頭とも 1）。
    """

    @property
    def label_name(self) -> str:
        """モデルに当てさせる列の名前。"""
        return TOP3

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``samples`` と同じ。"""
        # 着順なしは NaN にする（DuckDB の整数の欠損値 <NA> のままだと、比べた結果も欠損値になる）
        finish = as_numbers(samples["finish"])
        return pd.DataFrame({
            TOP3: finish.between(1, _LAST_PLACE).astype(int),
            WIN: (finish == 1).astype(int),
        }, index=samples.index)
