"""サブコマンドに共通の引数。"""

import argparse
from pathlib import Path

from 共通 import render


class CommonOptions:
    """出力（--format・--out）、元DB（--db）、学習済みモデルのフォルダ（--models）の引数を足す。"""

    def add_output(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT)
        parser.add_argument("--out", type=Path, default=None)

    def add_db(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--db", type=Path, default=None, help="元DBのパス（読むだけ）")

    def add_models(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--models", type=Path, required=True, help="学習済みモデルのフォルダ")
