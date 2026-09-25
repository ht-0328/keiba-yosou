"""python -m yosou.custom_binary の入口。"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from 共通 import cli, render

from . import workflow
from .feature.registrations import default_registry


class CommandLine:
    def run(self, argv: Sequence[str] | None = None) -> None:
        cli.run(self.parser(), self.execute, argv)

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="YAMLと特徴量テキストで設定する予想モデル", allow_abbrev=False)
        commands = parser.add_subparsers(dest="command", required=True)
        features = commands.add_parser("features", help="使用可能な特徴量", allow_abbrev=False)
        train = commands.add_parser("train", help="指定した条件で学習", allow_abbrev=False)
        train.add_argument("--config", type=Path, required=True, help="設定YAMLファイル")
        predict = commands.add_parser("predict", help="保存した条件で予想", allow_abbrev=False)
        predict.add_argument("race_id", help="16桁のレースID")
        predict.add_argument("--pops", nargs="+", help="馬番:人気（木曜は馬名:人気）")
        predict.add_argument("--odds", nargs="+", help="馬番:単勝オッズ")
        evaluate = commands.add_parser("evaluate", help="未学習のテスト期間で評価", allow_abbrev=False)
        for command in (features, train, predict, evaluate):
            command.add_argument("--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT)
            command.add_argument("--out", type=Path, default=None)
        for command in (train, predict, evaluate):
            command.add_argument("--db", type=Path, default=None, help="元DBのパス（読むだけ）")
        for command in (predict, evaluate):
            command.add_argument("--models", type=Path, required=True, help="学習済みモデルのフォルダ")
        return parser

    def execute(self, args: argparse.Namespace) -> None:
        registry = default_registry()
        if args.command == "features":
            result = render.Table.from_records([{
                "正式名称": feature.name, "説明": feature.description, "型": feature.kind.value,
                "利用可能時点": feature.known_from.label, "依存項目": " / ".join(feature.dependencies),
            } for feature in registry.definitions.values()], title="選択可能な特徴量")
        elif args.command == "train":
            result = workflow.train(args.config, args.db, registry)
        elif args.command == "predict":
            result = workflow.predict(args.race_id, args.models, args.db, registry, args.pops, args.odds)
        else:
            result = workflow.test_evaluation(args.models, args.db, registry)
        cli.emit(result, args)
