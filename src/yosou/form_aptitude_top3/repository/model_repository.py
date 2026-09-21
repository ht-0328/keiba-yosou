"""学習済みモデルのファイルを読み書きする。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ..setting import HyperparameterSettings

if TYPE_CHECKING:  # 型の注釈にだけ使う（実行時に読み込むと、パッケージの参照が循環する）
    from ..feature import PredictionTiming
    from ..ml_model import ProbabilityModel

#: 学習に使った設定を書くファイルの名前。
SETTINGS_FILE = "settings.json"


class ModelRepository:
    """時点ごとの学習済みモデルと、学習に使った設定を、ファイルに書き込む・読み込む（設計書 12・13 の 6）。

    置き場所は ``<root>/<時点>/``。1つのフォルダに、モデルごとのファイルと設定（settings.json）を置く。
    モデルは JV-Data から作ったもので公開しないので、``root`` は Git の対象外（``reports/``）にする。
    ``model_types`` は、読み込むモデルのクラス（LightGBM と CatBoost）。
    """

    def __init__(self, root: Path, model_types: Sequence[type[ProbabilityModel]]) -> None:
        self._root = Path(root)
        self._model_types = tuple(model_types)

    def save(self, timing: PredictionTiming, models: Sequence[ProbabilityModel],
             settings: HyperparameterSettings) -> Path:
        """その時点のモデルと設定を書き、書いたフォルダを返す。前に学習したものがあれば置き換える。"""
        folder = self._folder(timing)
        folder.mkdir(parents=True, exist_ok=True)
        for model in models:
            model.save(folder / model.file_name)
        text = json.dumps(settings.to_dict(), ensure_ascii=False, indent=2)
        (folder / SETTINGS_FILE).write_text(text + "\n", encoding="utf-8")
        return folder

    def load(self, timing: PredictionTiming) -> list[ProbabilityModel]:
        """その時点のモデルを読む。ファイルが無ければ ``FileNotFoundError``。"""
        folder = self._folder(timing)
        self._check_files(folder, timing)
        saved = json.loads((folder / SETTINGS_FILE).read_text(encoding="utf-8"))
        settings = HyperparameterSettings.from_dict(saved)
        return [model_type.load(folder / model_type.file_name, settings)
                for model_type in self._model_types]

    def _check_files(self, folder: Path, timing: PredictionTiming) -> None:
        file_names = [SETTINGS_FILE, *(model_type.file_name for model_type in self._model_types)]
        missing = [name for name in file_names if not (folder / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"{timing.label}の学習済みモデルがありません（{folder / missing[0]}）。"
                "先に train で学習してください。"
            )

    def _folder(self, timing: PredictionTiming) -> Path:
        return self._root / timing.value
