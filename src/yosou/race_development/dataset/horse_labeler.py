"""1頭ごとの5つの目的変数をまとめて付ける。"""

from __future__ import annotations

import pandas as pd

from . import label_names as names
from .early_position_labeler import EarlyPositionLabeler
from .finish_labeler import FinishLabeler
from .late_labeler import LateLabeler


class HorseLabeler:
    """1頭ごとの学習データ（①②④⑤⑦）の目的変数を、1回でまとめて付ける。``TargetLabeler`` を守る。

    共通の ``DatasetBuilder`` は目的変数の付け方を1つだけ受け取るので、3つのクラスの結果を横に並べる。
    予想ごとに当てさせる列は、あとで ``TrainingData.with_label()`` で持ち替える（設計書 04 の 1）。
    """

    def __init__(self) -> None:
        self._labelers = (EarlyPositionLabeler(), LateLabeler(), FinishLabeler())

    @property
    def label_name(self) -> str:
        """既定で当てさせる列（① 先頭）。"""
        return names.LEADER

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        return pd.concat([labeler.build(samples) for labeler in self._labelers], axis=1)
