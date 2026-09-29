"""predict: 保存した条件で1レースを予想する。"""

import argparse

from 共通 import db
from 共通.render import Table

from ..feature.registrations import default_registry
from ..workflow import LoadedModel, PredictionWorkflow
from .common_options import CommonOptions
from .prediction_table import PredictionTable


class PredictCommand:
    """``predict``: 対象の馬ごとの確率と期待値を、確率の高い順に出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("predict", help="保存した条件で予想", allow_abbrev=False)
        parser.add_argument("race_id", help="16桁のレースID")
        parser.add_argument("--pops", nargs="+", help="馬番:人気（木曜は馬名:人気）")
        parser.add_argument("--odds", nargs="+", help="馬番:単勝オッズ")
        options = CommonOptions()
        options.add_output(parser)
        options.add_db(parser)
        options.add_models(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> Table:
        """モデルを読んでから元DB を開き、予想し終えたら閉じる。"""
        registry = default_registry()
        model = LoadedModel.load(args.models, registry)
        with db.open_db(args.db) as con:
            result = PredictionWorkflow(con, registry).run(args.race_id, model, args.pops, args.odds)
        return PredictionTable(model.settings).table(result)
