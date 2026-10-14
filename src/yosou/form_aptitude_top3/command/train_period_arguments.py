"""train の、学習データの期間の区切りの引数。"""

from __future__ import annotations

import argparse
from datetime import date

from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY, DEFAULT_TRAIN_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, TrainingPeriod

from ..dataset import ABILITY_TRAIN_FIRST_DAY


class TrainPeriodArguments:
    """学習データの期間の区切り（設計書 08 の 3）。古い順に ウォームアップ → 学習 → 検証 → テスト。

    今の材料（当日）の学習データは ``--train-from`` から、馬の力の材料（木曜・前日）の学習データは ``--ability-train-from`` から
    （ウォームアップはその前の年の1月1日から）。検証・テストの区切りは、どちらの学習データでも同じ。
    """

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="今の材料のウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=DEFAULT_TRAIN_FIRST_DAY,
            help=f"今の材料（当日）の学習データの最初の開催日（既定: {DEFAULT_TRAIN_FIRST_DAY}）",
        )
        group.add_argument(
            "--ability-train-from", type=date.fromisoformat, default=ABILITY_TRAIN_FIRST_DAY,
            help=f"馬の力の材料（木曜・前日）の学習データの最初の開催日（既定: {ABILITY_TRAIN_FIRST_DAY}。"
                 "ウォームアップはその前の年の1月1日から）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )

    def form_period_of(self, args: argparse.Namespace) -> TrainingPeriod:
        """今の材料（当日）の学習データの期間。"""
        return TrainingPeriod.starting(args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from)

    def ability_period_of(self, args: argparse.Namespace) -> TrainingPeriod:
        """馬の力の材料（木曜・前日）の学習データの期間。"""
        return TrainingPeriod.starting(args.ability_train_from, args.valid_from, args.test_from)
