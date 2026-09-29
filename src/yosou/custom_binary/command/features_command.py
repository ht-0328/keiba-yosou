"""features: 選べる特徴量の一覧を出す。"""

import argparse

from 共通 import render

from ..feature.registrations import default_registry
from .common_options import CommonOptions


class FeaturesCommand:
    """``features``: 登録された特徴量の、正式名称・説明・型・利用可能時点・依存項目。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("features", help="使用可能な特徴量", allow_abbrev=False)
        CommonOptions().add_output(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> render.Table:
        registry = default_registry()
        return render.Table.from_records([{
            "正式名称": feature.name, "説明": feature.description, "型": feature.kind.value,
            "利用可能時点": feature.known_from.label, "依存項目": " / ".join(feature.dependencies),
        } for feature in registry.definitions.values()], title="選択可能な特徴量")
