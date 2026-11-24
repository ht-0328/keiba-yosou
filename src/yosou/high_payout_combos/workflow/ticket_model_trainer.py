"""1つの券種のモデルを学習する。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from ..dataset import ModelDataFactory


class TicketModelTrainer:
    """1つの券種の学習の行と検証の行（どちらも ``MissSampling`` で重みを付けた組の表）から、LightGBM と CatBoost を1つずつ学習する。

    どちらも市場の確率のロジット（``baseline``）を出発点にして、そこからの上げ下げだけを学ぶ。木の数は、検証の行で早期終了して決める。
    学習そのものは共有のモデルのクラス（``yosou.shared.ml_model``）が行う。戻り値は学習済みのモデル（LightGBM・CatBoost の順）。
    """

    def __init__(self, ticket_type: TicketType, settings: HyperparameterSettings) -> None:
        self._factory = ModelDataFactory(ticket_type)
        self._settings = settings

    def fit(self, train_rows: pd.DataFrame, valid_rows: pd.DataFrame) -> list[ProbabilityModel]:
        train, valid = self._factory.training(train_rows), self._factory.training(valid_rows)
        return [model_type.from_settings(self._settings).fit(train, valid) for model_type in MEMBER_TYPES]
