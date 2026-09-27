"""既存の予想の、単位ごと・時点ごとの学習済みモデルを、ファイルに読み書きする。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import ModelRepository
from yosou.shared.setting import HyperparameterSettings

from .tendency_source import TendencySource
from .tendency_unit import TendencyUnit

#: 展開の予想のモデルの置き場所の中で、既存の予想のモデルを置くフォルダ。
TENDENCY_FOLDER = "tendency"


class TendencyModelStore:
    """学習済みモデルを ``<root>/tendency/<既存の予想>/<単位>/<時点>/`` に書き、読む。

    既存の予想のコマンド（``yosou.<名前> train``）が保存するモデルとは別に持つ。展開の予想の学習データに入れた
    既存の予想の予測は、年ごとに学習し直したモデルのものなので、予測にも同じ作り方（予測する年のモデル）を使うためである。
    モデルは JV-Data から作ったものなので、``root`` は Git の対象外にする。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root) / TENDENCY_FOLDER

    def save(self, source: TendencySource, unit: TendencyUnit, timing: PredictionTiming, members: list[Any],
             settings: HyperparameterSettings) -> Path:
        return self._repository(source, unit).save(timing, members, settings)

    def load(self, source: TendencySource, unit: TendencyUnit, timing: PredictionTiming) -> list[Any]:
        """その単位・時点の2つのモデル。無ければ ``FileNotFoundError``（先に train で学習する）。"""
        return self._repository(source, unit).load(timing)

    def _repository(self, source: TendencySource, unit: TendencyUnit) -> ModelRepository:
        return ModelRepository(self._root / source.value / unit.folder, unit.member_types)
