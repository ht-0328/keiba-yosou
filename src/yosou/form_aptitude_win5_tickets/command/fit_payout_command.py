"""fit-payout: 配当の見積もりの式を作る。"""

from __future__ import annotations

import argparse
from datetime import date

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments

from ..payout import CARRY_LOG, FEATURE_COLUMNS, INVERSE_LOG, PayoutEstimator, PayoutTrainingRows
from ..repository import PayoutEstimatorRepository, Win5HistoryRepository
from ..repository.win5_columns import PAYOUT, RACE_DATE
from .yosou_name import YOSOU_NAME


class FitPayoutCommand:
    """``fit-payout``: ``--before`` の日より前の WIN5 の当たり組で配当の見積もりの式（``PayoutEstimator``）を作り、
    ``PayoutEstimatorRepository`` で ``payout_estimator.json`` に保存する（設計書 05 の図1）。式の傾き・切片・外れの散らばり・
    使った回数の表を返す。元DB は過去の WIN5 を読み終えたら閉じる。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("fit-payout", help="過去の WIN5 の当たり組から、配当の見積もりの式を作る", allow_abbrev=False)
        parser.add_argument("--before", type=date.fromisoformat, default=None,
                            help="この日より前の WIN5 で式を作る（YYYY-MM-DD。既定は今日）")
        CommonArguments(YOSOU_NAME, models_folder="").add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        before = args.before or date.today()
        with db.open_db(args.db) as con:
            history = Win5HistoryRepository(con).read(before)
        rows = PayoutTrainingRows().of(history)
        estimator = PayoutEstimator.fit(rows[list(FEATURE_COLUMNS)], rows[PAYOUT])
        period = {"最初の開催日": str(rows[RACE_DATE].min()), "最後の開催日": str(rows[RACE_DATE].max()), "この日より前": before.isoformat()}
        path = PayoutEstimatorRepository(args.models).save(estimator.to_dict(), period)
        return [self._table(estimator, period, history[RACE_DATE].nunique(), str(path))]

    def _table(self, estimator: PayoutEstimator, period: dict[str, str], day_count: int, path: str) -> Table:
        slope_inverse, slope_carry = estimator.slopes
        rows = [
            [f"傾き（{INVERSE_LOG}）", round(slope_inverse, 4)],
            [f"傾き（{CARRY_LOG}）", round(slope_carry, 4)],
            ["切片", round(estimator.intercept, 4)],
            ["戻すときの補正（exp(外れ) の平均）", round(estimator.smear, 4)],
            ["外れの散らばり（log の標準偏差）", round(estimator.residual_std, 4)],
            ["使った当たり組の数", estimator.count],
            ["読んだ WIN5 の回数（的中無の回を含む）", day_count],
            ["使った期間", f"{period['最初の開催日']} 〜 {period['最後の開催日']}（{period['この日より前']} より前）"],
            ["保存先", path],
        ]
        return Table(["項目", "値"], rows, title="配当の見積もりの式",
                     note="log(100円あたりの払戻) = 切片 + 傾き × 材料。戻すときは exp(式の値) × 補正。")
