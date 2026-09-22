"""サブコマンドに共通の引数。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import render

#: keiba-yosou のリポジトリ直下（src/yosou/shared/command/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]


class CommonArguments:
    """train と predict に共通の引数（--models --db --format --out）。ほかの道具（tools/）と同じ名前にそろえる。

    ``yosou_name`` は予想のパッケージ名（例: ``form_aptitude_top3``）。学習したモデルの既定の置き場所
    （``reports/<予想の名前>/models``）を決めるのに使う。
    """

    def __init__(self, yosou_name: str) -> None:
        self._yosou_name = yosou_name

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("共通")
        group.add_argument(
            "--models", type=Path, default=self._default_models_dir(),
            help=f"学習したモデルの置き場所（既定: reports/{self._yosou_name}/models）",
        )
        group.add_argument(
            "--db", type=Path, default=None,
            help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）",
        )
        group.add_argument(
            "--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT,
            help="出力の形式（既定: markdown）",
        )
        group.add_argument(
            "--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）",
        )

    def _default_models_dir(self) -> Path:
        """学習したモデルの既定の置き場所。JV-Data から作ったもので公開しないので、Git の対象外（reports/）に置く。"""
        return _PROJECT_ROOT / "reports" / self._yosou_name / "models"
