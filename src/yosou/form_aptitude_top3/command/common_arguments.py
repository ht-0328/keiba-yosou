"""サブコマンドに共通の引数。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import render

#: keiba-yosou のリポジトリ直下（src/yosou/form_aptitude_top3/command/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 学習したモデルの既定の置き場所。JV-Data から作ったもので公開しないので、Git の対象外（reports/）に置く。
DEFAULT_MODELS_DIR = _PROJECT_ROOT / "reports" / "form_aptitude_top3" / "models"


class CommonArguments:
    """train と predict に共通の引数（--models --db --format --out）。ほかの道具（tools/）と同じ名前にそろえる。"""

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("共通")
        group.add_argument(
            "--models", type=Path, default=DEFAULT_MODELS_DIR,
            help="学習したモデルの置き場所（既定: reports/form_aptitude_top3/models）",
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
