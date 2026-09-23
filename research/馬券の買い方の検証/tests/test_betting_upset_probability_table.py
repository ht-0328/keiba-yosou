"""契約: 荒れ具合の4つの確率の行列が、1レースの予測と同じ列（券種・固い〜超荒れ・いちばん高いクラス・中荒れ以上の確率）の表になる。"""

import numpy as np

from yosou.upset_level.dataset import BetType
from yosou.upset_level.workflow import PREDICTION_COLUMNS, TOP_LEVEL, UPSET_OR_MORE

from 馬券の買い方の検証.analysis.prediction import UpsetProbabilityTable


def test_columns_top_level_and_upset_or_more():
    probabilities = np.array([[0.6, 0.2, 0.15, 0.05], [0.1, 0.3, 0.4, 0.2]])
    table = UpsetProbabilityTable(BetType.TRIO).build(probabilities)
    assert list(table.columns) == list(PREDICTION_COLUMNS)
    assert list(table["券種"]) == ["3連複", "3連複"]
    assert list(table[TOP_LEVEL]) == ["固い", "大荒れ"]
    assert np.allclose(table[UPSET_OR_MORE], [0.4, 0.9])
    assert np.allclose(table["中荒れ"], [0.2, 0.3])
