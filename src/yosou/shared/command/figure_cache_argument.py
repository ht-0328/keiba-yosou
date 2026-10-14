"""train と predict に共通の引数 --figure-cache（馬の力の材料を使う予想が共通で使う）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..repository.speed_figure_repository import DEFAULT_FOLDER


class FigureCacheArgument:
    """``--figure-cache``: 馬の力の材料（全部の時点のモデル）が使う、スピード指数をとっておく場所。

    既定は道具「能力指数」と同じ ``reports/能力指数/cache/``（ファイルを共有する）。テストでは一時フォルダを渡し、
    本物のとっておいたファイルを書き換えない。中央の予想・重賞の傾向の予想・特別登録の予想が同じ引数を使うので ``shared`` に置く。
    """

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--figure-cache", type=Path, default=DEFAULT_FOLDER,
            help="スピード指数をとっておく場所（既定: reports/能力指数/cache。全部の時点のモデルが使う）",
        )
