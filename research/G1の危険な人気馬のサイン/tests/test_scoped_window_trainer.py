"""学ぶ範囲を絞り、予測は全部の行に出す区切りごとの学習。合成データとにせのモデルだけを使う。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PART_VALID
from 既存モデルの改善.analysis.windows import TestWindow

from G1の危険な人気馬のサイン.analysis.race_scope import G1_ONLY
from G1の危険な人気馬のサイン.analysis.scoped_window_trainer import ScopedWindowTrainer
from G1の危険な人気馬のサイン.analysis.sign_training_table import GRADE


class _FakeModel:
    """学習に渡された行の数を覚え、どの行にも 0.5 を返すにせのモデル。"""

    name = "にせ"
    tree_count = 1
    fitted: list[tuple[int, int]] = []

    @classmethod
    def from_settings(cls, settings):
        return cls()

    def fit(self, train: TrainingData, valid: TrainingData):
        _FakeModel.fitted.append((len(train), len(valid)))
        return self

    def predict_proba(self, data: TrainingData) -> np.ndarray:
        return np.full(len(data), 0.5)


def _data() -> TrainingData:
    days = [pd.Timestamp(year, 6, 1) for year in (2018, 2019, 2020) for _ in range(4)]
    grades = ["A", "B", "", "C"] * 3
    ids = pd.DataFrame({RACE_ID: [f"r{i}" for i in range(12)], RACE_DATE: days, HORSE_ID: [f"h{i}" for i in range(12)],
                        HORSE_NO: 1})
    features = pd.DataFrame({"x": np.arange(12, dtype=float)})
    catalog = FeatureCatalog((Feature("x", "A", FeatureKind.NUMERIC),))
    return TrainingData(ids, features, pd.DataFrame({"y": [0, 1] * 6}), pd.DataFrame({GRADE: grades}), catalog, "y")


def test_learns_only_the_scope_and_predicts_every_row():
    _FakeModel.fitted = []
    window = TestWindow("2020年", date(2019, 1, 1), date(2020, 1, 1), date(2020, 12, 31))
    variant = ModelVariant("t", "g1", "G1だけ", ("x",), uses_baseline=False)
    frame, logs = ScopedWindowTrainer(None, G1_ONLY, member_types=(_FakeModel,)).run(_data(), window, variant)
    # 学習は 2018年の G1 の1行、木を足すのを止める判断は 2019年の G1 の1行
    assert _FakeModel.fitted == [(1, 1)]
    # 予測は検証（2019年）とテスト（2020年）の全部の行
    assert frame[PART].value_counts().to_dict() == {PART_VALID: 4, PART_TEST: 4}
    assert logs[0]["学習の行数"] == 1
