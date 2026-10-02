"""目的変数（どのグループに入るか）を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from .column_names import IN_THE_MONEY, OUT_OF_THE_MONEY, WIN

#: 馬券内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE_IN_THE_MONEY = 3


class FinishGroupLabeler:
    """1番人気が、勝利・馬券内・馬券外のどのグループに入るかの列を付ける（設計書 10）。``TargetLabeler`` を守る。

    - 勝利: 確定着順が 1着なら 1。
    - 馬券内: 確定着順が 1〜3着なら 1（勝った馬も 1）。
    - 馬券外: 馬券内でなければ 1。着順の付かない競走中止・失格（着順が欠損値）も 1。
    - 同着は、どちらも同じ着順として扱う。
    """

    @property
    def label_name(self) -> str:
        """``TrainingData.label`` で返す列。この予想は3つの列を ``GROUPS`` の名前で直接使う。"""
        return OUT_OF_THE_MONEY

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``samples`` と同じ。"""
        # 着順なしは NaN にする（DuckDB の整数の欠損値 <NA> のままだと、比べた結果も欠損値になる）
        finish = as_numbers(samples["finish"])
        in_the_money = finish.between(1, _LAST_PLACE_IN_THE_MONEY)
        return pd.DataFrame({
            WIN: (finish == 1).astype(int),
            IN_THE_MONEY: in_the_money.astype(int),
            OUT_OF_THE_MONEY: (~in_the_money).astype(int),
        }, index=samples.index)
