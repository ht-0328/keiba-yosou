"""基準「1番人気のオッズだけの予想」を学習して測る。"""

from __future__ import annotations

from collections.abc import Sequence

from yosou.shared.dataset import SplitData, TrainingData
from yosou.shared.evaluation import ClassEvaluation, ClassModelEvaluator
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel, LightGbmMulticlassModel, Member
from yosou.shared.setting import HyperparameterSettings

from ..feature import FAVORITE_ODDS

#: 基準を測る時点。1番人気のオッズは前日から分かる。前日と当日は同じ列なので、当日の値も同じになる。
BASELINE_TIMING = PredictionTiming.DAY_BEFORE
#: 基準の特徴量の一覧（1番人気のオッズの1つだけ）。
_ODDS_ONLY_CATALOG = FeatureCatalog((Feature(FAVORITE_ODDS, "B", FeatureKind.NUMERIC, BASELINE_TIMING),))


class FavoriteOddsBaseline:
    """特徴量を「1番人気のオッズ」の1つだけにして、この予想と同じ手順（同じ設定の LightGBM と CatBoost、同じ学習データと
    検証データ）で学習し、検証データでの当たり具合を測る（設計書 16 の 3）。

    市場（オッズ）がすでに知っていること以上を、この予想の特徴量から学べているかを見るための基準である。
    木曜はオッズを使わないので、この基準は無い。学習したモデルは保存しない（比べるためだけに使う）。
    """

    def __init__(self, settings: HyperparameterSettings,
                 member_types: Sequence[type[Member]] = CLASS_MEMBER_TYPES) -> None:
        self._settings = settings
        self._member_types = tuple(member_types)

    def evaluate(self, split: SplitData) -> list[ClassEvaluation]:
        """学習データで学習し、検証データでモデルごとと平均の当たり具合を返す（時点は前日）。"""
        train = self._odds_only(split.train)
        valid = self._odds_only(split.valid)
        members = [model_type.from_settings(self._settings).fit(train, valid) for model_type in self._learnable(train)]
        return ClassModelEvaluator().evaluate(BASELINE_TIMING, EnsembleModel(members), valid)

    def _learnable(self, train: TrainingData) -> tuple[type[Member], ...]:
        """学習するモデルのクラス。1番人気のオッズが学習データで1通りしかないとき（合成DB など）は、CatBoost は
        「全部の特徴量が一定」で学習できないので、LightGBM だけにする（LightGBM はクラスの割合だけを学ぶ）。実DB では起きない。
        """
        if train.features[FAVORITE_ODDS].nunique() > 1:
            return self._member_types
        return (LightGbmMulticlassModel,)

    def _odds_only(self, data: TrainingData) -> TrainingData:
        """特徴量を1番人気のオッズだけにした学習データ。目的変数・評価用の列はそのまま。"""
        return TrainingData(
            data.ids, data.features[[FAVORITE_ODDS]], data.targets, data.evaluation,
            _ODDS_ONLY_CATALOG, data.label_name, data.class_labels, data.baseline,
        )
