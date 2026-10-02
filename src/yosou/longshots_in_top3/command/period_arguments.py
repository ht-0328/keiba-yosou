"""学習データの期間の区切りの引数（train と calibration で同じもの）。"""

from __future__ import annotations

import argparse
from datetime import date

from yosou.shared.dataset import (
    DEFAULT_TEST_FIRST_DAY,
    DEFAULT_TRAIN_FIRST_DAY,
    DEFAULT_VALID_FIRST_DAY,
    TrainingPeriod,
)


class PeriodArguments:
    """学習データの期間の区切り（設計書 08 の 4）の引数を足し、読んだ値から ``TrainingPeriod`` を作る。

    古い順に ウォームアップ → 学習 → 検証 → テスト。calibration（確率のずれの確認）は、学習のときと同じ区切りを渡すと、
    学習に使っていない検証・テストの期間で測れる。
    """

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="ウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=DEFAULT_TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {DEFAULT_TRAIN_FIRST_DAY}）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )

    def period(self, args: argparse.Namespace) -> TrainingPeriod:
        return TrainingPeriod.starting(args.train_from, args.valid_from, args.test_from,
                                       warmup_first_day=args.warmup_from)
