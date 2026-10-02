"""train と predict に共通の引数 --development-root。"""

from __future__ import annotations

import argparse
from pathlib import Path

#: keiba-yosou のリポジトリ直下（src/yosou/form_aptitude_top3/command/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 予想「展開から着順を予想」の置き場所の既定（``yosou.race_development`` の ``YOSOU_NAME`` と同じ名前）。
DEFAULT_DEVELOPMENT_ROOT = _PROJECT_ROOT / "reports" / "展開から着順を予想"


class DevelopmentRootArgument:
    """``--development-root``: 展開の予想の結果（まとまり P）を使う時点のモデルが読む、予想「展開から着順を予想」の置き場所。

    学習（train）は ``<置き場所>/out_of_sample/``（年ごとの確かめの予測）を、予測（predict）は ``<置き場所>/models/``
    （保存した展開のモデル）を読む。テストでは一時フォルダを渡す。
    """

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
            help="予想「展開から着順を予想」の置き場所（既定: reports/展開から着順を予想。木曜のモデルが展開の予想の結果を読む）",
        )
