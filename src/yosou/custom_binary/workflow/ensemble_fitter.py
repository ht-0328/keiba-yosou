"""学習期間で2つのモデルを学び、検証期間で早期終了を決める。"""

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel

from ..setting import ModelSettings


class EnsembleFitter:
    """学習データを時期で分け、LightGBM と CatBoost を学ぶ。保存はしない（探索で何通りも試すときにも使う）。

    学習・検証のデータが空・正解が1クラスだけ・特徴量が設定と違う・すべて同じ値のときは、学ぶ前に止める。
    """

    def fit(self, data: TrainingData, settings: ModelSettings) -> tuple[EnsembleModel, TrainingData, TrainingData]:
        """（2つのモデルの平均、学習データ、検証データ）を返す。"""
        period = settings.period
        train = data.between(period.train_first_day, period.valid_first_day)
        valid = data.between(period.valid_first_day, period.test_first_day)
        for name, part in (("学習", train), ("検証", valid)):
            self._check_part(name, part)
        if list(data.features.columns) != list(settings.selected):
            raise ValueError("学習データの特徴量が指定と違います")
        if (data.baseline is not None) != settings.odds_baseline:
            raise ValueError("学習データの基準確率（オッズ）の有無が設定のodds_baselineと違います")
        if not train.features.nunique(dropna=False).gt(1).any():
            raise ValueError("学習データの特徴量がすべて同じ値です。変化のある項目を選んでください")
        models = [model_type.from_settings(settings.parameters).fit(train, valid) for model_type in MEMBER_TYPES]
        return EnsembleModel(models), train, valid

    def _check_part(self, name: str, part: TrainingData) -> None:
        if not len(part):
            raise ValueError(f"{name}データが空です。期間・人気範囲・条件を確認してください")
        if part.label.nunique() != 2:
            raise ValueError(f"{name}データの正解が1クラスだけです。期間・人気範囲・条件を広げてください")
