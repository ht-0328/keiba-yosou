"""騎手・調教師・血統を「市場の期待をどれだけ上回ったか」の数値にする。"""

from __future__ import annotations

import pandas as pd


class MarketExcessRate:
    """ある区分（騎手・調教師・父・母父）が、市場の期待をどれだけ上回ってきたかを1つの数値にする。

    騎手コードをそのままカテゴリ特徴量として渡すと、モデルは名前を覚えるだけになり、
    学習データの当たり具合は上がるのに、新しい年では効かなくなる（実測でログ損失が悪化した）。

    代わりに「その騎手が乗った馬は、市場が付けた確率より実際にどれだけ多く来たか」を数値にする。
    市場の確率をあらかじめ引いてあるので、残るのは市場が見落としている分だけになる。
    これは「人・血統を特徴量から外す」のではなく、**表し方を変える**ということである。

    その出走より前の結果だけを使う（同じ開催日でも、前のレースの結果は買う時点で分かっている）。
    出走数の少ない区分は値が暴れるので、``shrink`` の分だけ 0 に引き寄せる。
    """

    def __init__(self, shrink: float = 200.0) -> None:
        self._shrink = shrink

    def build(self, frame: pd.DataFrame, group_column: str, actual_column: str,
              expected_column: str) -> pd.Series:
        """``group_column`` ごとの、これまでの「実際 − 市場の期待」の平均。

        ``frame`` は ``race_date``・``race_no``・``horse_no`` を持つ表。
        ``actual_column`` は結果（3着以内なら 1）、``expected_column`` は市場が付けた確率。
        """
        order = frame.sort_values(["race_date", "race_no", "horse_no"]).index
        ordered = frame.loc[order, [group_column, actual_column, expected_column]]
        grouped = ordered.groupby(group_column, observed=True)
        actual_before = grouped[actual_column].cumsum() - ordered[actual_column]
        expected_before = grouped[expected_column].cumsum() - ordered[expected_column]
        count_before = grouped.cumcount()
        excess = (actual_before - expected_before) / (count_before + self._shrink)
        return excess.reindex(frame.index)
