"""train: 予測に使うモデルを学習して保存する。"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

from 共通.render import Table

from yosou.shared.feature import PredictionTiming

from ..workflow import DevelopmentTrainingWorkflow, SavedModel
from .yosou_name import PROJECT_ROOT, YOSOU_NAME

#: 時点の書き方の案内。
_TIMING_CHOICES = " / ".join(f"{timing.label}（{timing.value}）" for timing in PredictionTiming)


class TrainCommand:
    """``train``: 時点ごとに、7つの予想の LightGBM と CatBoost を学習して保存する（設計書 05 の図1）。

    学習するのは ``--year`` 年のモデル（学習は組の最初の年 〜 前の年の9月、検証は前の年の10〜12月）。
    後半と着順のモデルの学習データに入れる前の組の予測は、年ごとに学習し直して作る（年ごとの確かめと共有し、作ったものは読むだけ）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("train", help="時点ごとに7つの予想のモデルを学習して保存する", allow_abbrev=False)
        parser.add_argument("--year", type=int, default=date.today().year,
                            help="学習するモデルの年（既定: 今年。前の年の12月までのデータで学習する）")
        parser.add_argument("--timings", nargs="*", default=None, metavar="時点",
                            help=f"学習する時点: {_TIMING_CHOICES}（省略すると3つ全部）")
        parser.add_argument("--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）")
        parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "reports" / YOSOU_NAME,
                            help=f"モデルと途中の結果の置き場所（既定: reports/{YOSOU_NAME}。Git の対象外）")
        parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        timings = [PredictionTiming.parse(text) for text in args.timings] if args.timings else list(PredictionTiming)
        saved = DevelopmentTrainingWorkflow(args.root, args.db, self._progress).run(args.year, timings, args.config)
        return [self._table(saved)]

    def _table(self, saved: list[SavedModel]) -> Table:
        rows = [[model.kind.spec.label_text, model.timing.label, str(model.folder), " / ".join(map(str, model.tree_counts)),
                 model.order_lambda if model.order_lambda is not None else ""] for model in saved]
        return Table(["予想", "時点", "置き場所", "木の数（LightGBM / CatBoost）", "λ（⑦ だけ）"], rows, title="保存したモデル")

    def _progress(self, message: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)
