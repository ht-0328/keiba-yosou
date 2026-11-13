"""predict の引数 --form-models（今のモデルの学習済みモデルの置き場所）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .yosou_name import FORM_YOSOU_NAME

#: keiba-yosou のリポジトリ直下（src/yosou/form_aptitude_win5_tickets/command/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 今のモデルの学習済みモデルの既定の置き場所（今のモデルのコマンドの既定と同じ）。
DEFAULT_FORM_MODELS = _PROJECT_ROOT / "reports" / FORM_YOSOU_NAME / "models"


class FormModelsArgument:
    """``--form-models``: 今のモデルの学習済みモデルの置き場所。この予想は読むだけで、書かない（学び直しは今のモデルの ``train``）。"""

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--form-models", type=Path, default=DEFAULT_FORM_MODELS,
            help=f"今のモデルの学習済みモデルの置き場所（既定: reports/{FORM_YOSOU_NAME}/models）",
        )
