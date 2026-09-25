"""学習データ（1番人気の行だけ・3つのグループの列）と、グループの付け方。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset.column_names import POPULARITY

from ..dataset import GROUPS, IN_THE_MONEY, OUT_OF_THE_MONEY, WIN, FinishGroupLabeler
from ..feature import CATALOG


def test_training_data_has_only_the_first_favorites(training_data):
    assert len(training_data) > 0
    assert (training_data.evaluation[POPULARITY] == 1).all()
    assert list(training_data.features.columns) == list(CATALOG.names)
    # 前走の人気（前走も1番人気だったか）は、特徴量に入っている
    assert "前走の人気" in training_data.features.columns
    assert set(training_data.features["芝ダ"].dropna()) <= {"芝", "ダート"}


def test_groups_are_consistent(training_data):
    targets = training_data.targets[list(GROUPS)]
    # 勝った馬は馬券内にも入る。馬券外は馬券内の反対
    assert (targets[WIN] <= targets[IN_THE_MONEY]).all()
    assert (targets[IN_THE_MONEY] + targets[OUT_OF_THE_MONEY] == 1).all()
    assert targets[WIN].sum() > 0 and targets[OUT_OF_THE_MONEY].sum() > 0


def test_labeler_puts_unfinished_runs_out_of_the_money():
    samples = pd.DataFrame({"finish": pd.array([1, 3, 4, None], dtype="Int64")})
    labels = FinishGroupLabeler().build(samples)
    assert labels[WIN].tolist() == [1, 0, 0, 0]
    assert labels[IN_THE_MONEY].tolist() == [1, 1, 0, 0]
    # 着順の付かない競走中止・失格は馬券外
    np.testing.assert_array_equal(labels[OUT_OF_THE_MONEY], [0, 0, 1, 1])
