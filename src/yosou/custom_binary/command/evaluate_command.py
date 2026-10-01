"""evaluate: 未学習のテスト期間で評価する。"""

import argparse

from 共通.render import Table

from ..evaluation import HISTORICAL_NOTE, PAYBACK_NOTE
from ..feature.default_registry import DefaultRegistry
from ..workflow import TestEvaluationWorkflow
from .common_options import CommonOptions


class EvaluateCommand:
    """``evaluate``: テスト期間の成績と回収率を出し、モデルのフォルダに ``test_evaluation.json`` を書く。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("evaluate", help="未学習のテスト期間で評価", allow_abbrev=False)
        options = CommonOptions()
        options.add_output(parser)
        options.add_db(parser)
        options.add_models(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        result = TestEvaluationWorkflow(DefaultRegistry().build(), args.db).run(args.models)
        return [
            Table.from_records(result["scores"], title="テスト期間の成績", note=HISTORICAL_NOTE),
            Table.from_records(result["paybacks"], title="テスト期間の回収率", note=PAYBACK_NOTE),
        ]
