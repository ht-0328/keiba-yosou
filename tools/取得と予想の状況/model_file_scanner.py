"""学習済みモデルの置き場所を見て、どのモデルがいつ作られたかを調べる。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from itertools import chain
from pathlib import Path

from 取得と予想の状況.model_folder import ModelFolder

#: 学習済みモデルのフォルダの印（``train`` が LightGBM・CatBoost と一緒に書く設定）。
MODEL_MARKER = "settings.json"


class ModelFileScanner:
    """``(予想の名前, 置き場所)`` の並びについて、置き場所の下の ``settings.json`` のあるフォルダを全部見つける。

    予想のコードは読み込まない（置き場所の中身を見るだけ）。予想（``forecast.py``）はモデルが無いと動かないので、
    無い置き場所は ``missing_roots`` で知らせる。
    """

    def __init__(self, roots: Sequence[tuple[str, Path]]) -> None:
        self._roots = tuple((yosou, Path(root)) for yosou, root in roots)

    def scan(self) -> list[ModelFolder]:
        """見つけたモデルを、予想の順・相対パスの順に。"""
        return list(chain.from_iterable(self._scan_root(yosou, root) for yosou, root in self._roots))

    def missing_roots(self) -> list[str]:
        """置き場所そのものが無い予想の名前。"""
        return [yosou for yosou, root in self._roots if not root.is_dir()]

    def _scan_root(self, yosou: str, root: Path) -> list[ModelFolder]:
        if not root.is_dir():
            return []
        folders = (self._folder(yosou, root, marker.parent) for marker in root.rglob(MODEL_MARKER))
        return sorted(folders, key=lambda folder: folder.relative)

    @staticmethod
    def _folder(yosou: str, root: Path, folder: Path) -> ModelFolder:
        newest = max(path.stat().st_mtime for path in folder.iterdir() if path.is_file())
        return ModelFolder(yosou, folder.relative_to(root).as_posix(), datetime.fromtimestamp(newest).replace(microsecond=0))
