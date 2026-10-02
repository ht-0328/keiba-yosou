"""train: 本番の予測に使うモデルを学習して保存する。"""

from __future__ import annotations

import argparse

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments

from ..repository import SimilarityModelRepository
from ..similarity import SimilarityModelSet
from ..workflow import SimilarityTraining, TrainingDataReader
from .settings_argument import SettingsArgument
from .yosou_name import YOSOU_NAME


class TrainCommand:
    """``train``: 方針の「学習の最初の年」から元DB の最後の開催日までの1番人気で、単位ごとの3つのモデルを作って保存する。"""

    def __init__(self) -> None:
        self._settings_argument = SettingsArgument()

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="単位ごとに勝利・馬券内・馬券外の3つのモデルを作って保存する", allow_abbrev=False,
        )
        self._settings_argument.add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。"""
        settings = self._settings_argument.settings(args)
        with db.open_db(args.db) as con:
            data = TrainingDataReader(settings).read(con)
        models = SimilarityTraining(settings).train(data)
        folder = SimilarityModelRepository(args.models).save(models)
        return [self._units_table(models, data.for_timing(settings.timing).features),
                Table(["保存した場所"], [[str(folder)]], title="保存したモデル")]

    def _units_table(self, models: SimilarityModelSet, features) -> Table:
        members = models.unit_map.members(features)
        rows = [[unit, "・".join(f"{d}m" for d in members.get(unit, [])), *model.group_rows().values()]
                for unit, model in models.units.items()]
        return Table(["単位", "含む距離", "勝利", "馬券内", "馬券外"], rows, title="単位ごとのグループの頭数",
                     note=f"学習データは {models.settings.train_first_year}年1月から。特徴量の時点は{models.settings.timing.label}。")
