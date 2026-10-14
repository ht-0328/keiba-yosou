"""train と backtest に共通の、学習データの期間の引数。"""

from __future__ import annotations

import argparse
from datetime import date

from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, TrainingPeriod

from ..dataset import TRAIN_FIRST_DAY, WARMUP_FIRST_DAY


class PeriodArguments:
    """学習データの期間の区切り（設計書 08 の 4）。古い順に ウォームアップ → 学習 → 検証 → テスト。

    学習データは1つなので、中央の予想の ``--ability-train-from`` は無い。ウォームアップの既定は DB にある最初の年（2011年1月1日）、
    学習の既定は 2012年1月1日。``with_split`` を偽にすると、検証・テストの区切りは受け取らない（7つの区切りでの確かめは区切りごとに決める）。
    """

    def __init__(self, with_split: bool = True) -> None:
        self._with_split = with_split

    def add_to(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=WARMUP_FIRST_DAY,
            help=f"ウォームアップ期間の最初の開催日（既定: {WARMUP_FIRST_DAY}）。この日からの出走を過去走・通算の成績・対戦レーティングの計算にだけ使い、サンプルにしない",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {TRAIN_FIRST_DAY}）",
        )
        if not self._with_split:
            return
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )

    def period_of(self, args: argparse.Namespace) -> TrainingPeriod:
        """引数から期間を作る。順になっていなければ ``ValueError``。検証・テストを受け取らないときは既定の日。"""
        valid_from = getattr(args, "valid_from", DEFAULT_VALID_FIRST_DAY)
        test_from = getattr(args, "test_from", DEFAULT_TEST_FIRST_DAY)
        return TrainingPeriod(args.warmup_from, args.train_from, valid_from, test_from)
