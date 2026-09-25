"""--config の引数。"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..setting import BuyOrFadeSettings


class SettingsArgument:
    """``--config``（方針の設定ファイル）を足し、読んだ方針を返す。train と evaluate で使う。"""

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--config", type=Path, default=None,
            help="方針の設定ファイル（TOML。書いた項目だけが初期値 setting/default_settings.toml から置き換わる）",
        )

    def settings(self, args: argparse.Namespace) -> BuyOrFadeSettings:
        return BuyOrFadeSettings.load(args.config)
