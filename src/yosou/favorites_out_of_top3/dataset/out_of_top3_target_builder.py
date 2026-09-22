"""目的変数を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from .column_names import OUT_OF_TOP3

#: 3着以内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE_IN_TOP3 = 3


class OutOfTop3TargetBuilder:
    """目的変数（設計書 10）。確定着順で決める。``TargetLabeler`` を守る。

    - 確定着順が 1〜3 なら 0（馬券になった）。
    - 確定着順が 4以上なら 1（馬券にならなかった）。
    - 着順の付かない競走中止・失格（着順が欠損値）も 1。走ったが馬券にならなかった点は同じだからである。
    - 出走しなかった馬（取消・除外）は、``FavoriteSelector`` がすでに除いている。
    - 同着は、どちらも同じ着順として扱う（3着同着なら 2頭とも 0）。
    """

    @property
    def label_name(self) -> str:
        """モデルに当てさせる列の名前。"""
        return OUT_OF_TOP3

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``samples`` と同じ。"""
        # 着順なしは NaN にする（DuckDB の整数の欠損値 <NA> のままだと、比べた結果も欠損値になる）
        finish = as_numbers(samples["finish"])
        is_top3 = finish.between(1, _LAST_PLACE_IN_TOP3)
        return pd.DataFrame({OUT_OF_TOP3: (~is_top3).astype(int)}, index=samples.index)
