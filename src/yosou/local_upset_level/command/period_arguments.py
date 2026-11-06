"""train の、学習データの期間の引数。"""

from __future__ import annotations

import argparse
from datetime import date

from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, TrainingPeriod

from ..dataset import LOCAL_UPSET_TRAIN_FIRST_DAY, LOCAL_UPSET_WARMUP_FIRST_DAY


class PeriodArguments:
    """学習データの期間の区切り（設計書 08 の 4）。古い順に ウォームアップ → 学習 → 検証 → テスト。

    既定は地方の全頭の予想と同じ（ウォームアップ 2016年1月1日・学習 2019年1月1日・検証 2025年7月1日・テスト 2026年1月1日から）。
    """

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=LOCAL_UPSET_WARMUP_FIRST_DAY,
            help=f"ウォームアップ期間の最初の開催日（既定: {LOCAL_UPSET_WARMUP_FIRST_DAY}）。この日からの出走を近走・過去の荒れ率・傾きの計算にだけ使い、サンプルにしない",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=LOCAL_UPSET_TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {LOCAL_UPSET_TRAIN_FIRST_DAY}）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )

    def period_of(self, args: argparse.Namespace) -> TrainingPeriod:
        """引数から期間を作る。順になっていなければ ``ValueError``。"""
        return TrainingPeriod(args.warmup_from, args.train_from, args.valid_from, args.test_from)
