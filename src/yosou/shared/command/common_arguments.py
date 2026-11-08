"""サブコマンドに共通の引数。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db, render

#: keiba-yosou のリポジトリ直下（src/yosou/shared/command/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]


class CommonArguments:
    """train と predict に共通の引数（--models --db --format --out）。ほかの道具（tools/）と同じ名前にそろえる。

    ``yosou_name`` は予想の名前（例: ``近走と適性から3着以内を予想``。各パッケージの ``yosou_name.py``）。
    学習したモデルの既定の置き場所（``reports/<予想の名前>/models``）を決めるのに使う。
    ``database`` は ``--db`` を省いたときの元DB（中央 ``db.JRA`` か地方 ``db.LOCAL``）。コマンドは ``db.open_db(args.db, default=database)`` で開く。
    ``models_folder`` は ``reports/<予想の名前>/`` の下の、``--models`` の既定のフォルダ名。空文字なら ``reports/<予想の名前>`` そのもの
    （学習済みモデルを持たず、配当の見積もりの式と記録だけを置く予想「近走と適性からWIN5の買い目を決める」）。
    """

    def __init__(self, yosou_name: str, database: db.DatabaseDefault = db.JRA, models_folder: str = "models") -> None:
        self._yosou_name = yosou_name
        self.database = database
        self._models_folder = models_folder

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("共通")
        group.add_argument(
            "--models", type=Path, default=self._default_models_dir(),
            help=f"学習したモデルの置き場所（既定: {self._default_models_text()}）",
        )
        group.add_argument("--db", type=Path, default=None, help=self.database.help())
        group.add_argument(
            "--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT,
            help="出力の形式（既定: markdown）",
        )
        group.add_argument(
            "--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）",
        )

    def _default_models_dir(self) -> Path:
        """学習したモデルの既定の置き場所。JV-Data から作ったもので公開しないので、Git の対象外（reports/）に置く。"""
        root = _PROJECT_ROOT / "reports" / self._yosou_name
        return root / self._models_folder if self._models_folder else root

    def _default_models_text(self) -> str:
        """``--help`` に出す既定の置き場所。"""
        root = f"reports/{self._yosou_name}"
        return f"{root}/{self._models_folder}" if self._models_folder else root
