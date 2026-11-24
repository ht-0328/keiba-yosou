"""券種ごとの学習済みモデルのファイルを読み書きする。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from yosou.shared.betting import TicketType
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.repository import ModelRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.setting import HyperparameterSettings

#: モデルを置く時点のフォルダ。この予想は券種のオッズの板が要るので、当日（締め切り前）の1つだけ。
_TIMING = PredictionTiming.RACE_DAY


class TicketModelRepository:
    """券種ごとの学習済みモデル（LightGBM と CatBoost）を ``<folder>/<券種の英名>/race_day/`` に置く。

    ファイルの形は共有の ``ModelRepository`` と同じ（モデルごとのファイルと、学習に使った設定 settings.json）。
    共有のクラスは時点までしか知らないので、券種ごとに1つずつ作って置き場所を変える。
    例: 馬連のモデルは ``<folder>/quinella/race_day/lightgbm.joblib``・``catboost.cbm``・``settings.json``。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def save(self, ticket_type: TicketType, models: Sequence[ProbabilityModel], settings: HyperparameterSettings) -> Path:
        """その券種のモデルと設定を書き、書いたフォルダを返す。"""
        return self._repository(ticket_type).save(_TIMING, models, settings)

    def load(self, ticket_type: TicketType) -> list[ProbabilityModel]:
        """その券種のモデル（LightGBM・CatBoost の順）。無ければ ``FileNotFoundError``。"""
        return self._repository(ticket_type).load(_TIMING)

    def has(self, ticket_type: TicketType) -> bool:
        """その券種のモデルが保存してあるか（設定のファイルと、モデルごとのファイルが全部あるか）。"""
        folder = self._folder / ticket_type.key / _TIMING.value
        file_names = [SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)]
        return all((folder / name).exists() for name in file_names)

    def _repository(self, ticket_type: TicketType) -> ModelRepository:
        return ModelRepository(self._folder / ticket_type.key, MEMBER_TYPES)
