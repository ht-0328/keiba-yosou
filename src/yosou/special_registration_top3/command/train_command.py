"""train: 学習する。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.ability_score import AbilityScoreAttachment
from yosou.shared.command import CommonArguments, FigureCacheArgument, TrainingReportTables
from yosou.shared.dataset import TrainingPeriod, WinTargetData
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import registration_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMING_LABELS, TIMINGS, WIN_FOLDER
from .period_arguments import PeriodArguments
from ..yosou_name import YOSOU_NAME

#: 表の題に付ける、材料の名前と 1着のモデルの言葉。
SUBJECT = "特別登録の材料"
_WIN_SUBJECT = "1着"


class TrainCommand:
    """``train``: 特別登録の時点の 3着以内のモデルと1着のモデル（LightGBM と CatBoost）を学習して保存し、検証データでの当たり具合を出す。

    学習データは1つ（``registration_dataset_builder``。M 168個・O 7個・Y 1個）で、学ぶ前に T（能力スコア）の4個を足す
    （``AbilityScoreAttachment``。180個。設計書 05 の図1）。同じ学習データで、3着以内のモデルと、目的変数を「1着」に持ち替えた
    1着のモデル（``WinTargetData``。オッズが無いので基準は無し）を別々に学び、1着のモデルは ``<置き場所>/1着/`` に保存する（設計書 10）。
    券種オッズなしのモデルと複勝の見込みの倍率は無い（オッズを使わない）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("train", help="特別登録の時点の 3着以内と1着のモデルを学習して保存する", allow_abbrev=False)
        parser.add_argument(
            "--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        PeriodArguments().add_to(parser)
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        period = PeriodArguments().period_of(args)
        with db.open_db(args.db) as con:
            data = registration_dataset_builder(con, args.figure_cache).build_training_data(period)
        data = AbilityScoreAttachment().apply(data)
        top3 = self._workflow(period, args.models).train(data, args.config)
        win = self._workflow(period, args.models / WIN_FOLDER).train(WinTargetData().training(data), args.config)
        return [*TrainingReportTables(top3, SUBJECT, TIMING_LABELS).tables(),
                *TrainingReportTables(win, f"{_WIN_SUBJECT}: {SUBJECT}", TIMING_LABELS).tables()]

    def _workflow(self, period: TrainingPeriod, root: Path) -> TrainingWorkflow:
        """読んだ学習データで学ぶだけの学習の流れ（学習データは作らない）。"""
        return TrainingWorkflow(None, period, ModelRepository(root, MEMBER_TYPES), TIMINGS, DEFAULT_SETTINGS_PATH)
