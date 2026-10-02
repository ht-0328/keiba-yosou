"""学習した近さのモデルの一式を、ファイルに書き込む・読み込む。"""

from __future__ import annotations

import pickle
from pathlib import Path

from ..similarity import SimilarityModelSet

#: 一式を書くファイルの名前。
MODEL_FILE = "similarity_models.pkl"
#: 学習に使った方針を、人が読める形で書くファイルの名前。
SETTINGS_FILE = "settings.json"


class SimilarityModelRepository:
    """近さのモデルの一式（単位の決め方・単位ごとの3つのモデル・方針）の置き場所（設計書 04）。

    置き場所は ``<root>/``。モデルは JV-Data から作ったもので公開しないので、``root`` は Git の対象外（``reports/``）にする。
    自分で書いたファイルだけを読む（pickle は、知らないファイルを読むと危ないため）。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def save(self, models: SimilarityModelSet) -> Path:
        """一式と方針を書き、書いたフォルダを返す。前に学習したものがあれば置き換える。"""
        self._root.mkdir(parents=True, exist_ok=True)
        with (self._root / MODEL_FILE).open("wb") as file:
            pickle.dump(models, file)
        (self._root / SETTINGS_FILE).write_text(models.settings.to_json() + "\n", encoding="utf-8")
        return self._root

    def load(self) -> SimilarityModelSet:
        """一式を読む。無ければ ``FileNotFoundError``。"""
        path = self._root / MODEL_FILE
        if not path.exists():
            raise FileNotFoundError(f"学習済みのモデルがありません（{path}）。先に train で学習してください。")
        with path.open("rb") as file:
            return pickle.load(file)
