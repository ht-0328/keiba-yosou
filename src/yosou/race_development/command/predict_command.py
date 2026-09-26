"""predict: 1レースの展開と着順を予測し、印と買い目を出す。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from 共通.render import Table

from yosou.shared.feature import PredictionTiming

from ..workflow import DevelopmentForecast, DevelopmentPredictionWorkflow
from .yosou_name import PROJECT_ROOT, YOSOU_NAME

#: 時点の書き方の案内。
_TIMING_CHOICES = " / ".join(f"{timing.label}（{timing.value}）" for timing in PredictionTiming)
#: 確率の列（表で丸める）。
_ROUNDED_DIGITS = 3


class PredictCommand:
    """``predict``: 1レースを、その時点のモデルで前半 → 後半 → 着順の順に予測し、印と印どおりの買い目を出す（設計書 05 の図2）。

    予測のたびに、予測用データと予測を ``reports/race_development/predictions/`` に書き足す。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("predict", help="1レースの展開と着順を予測し、印と買い目を出す", allow_abbrev=False)
        parser.add_argument("race_id", help="レースID（16桁）")
        parser.add_argument("--timing", required=True, help=f"予測する時点: {_TIMING_CHOICES}")
        parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "reports" / YOSOU_NAME,
                            help=f"モデルの置き場所（<root>/models）と予測の記録の置き場所（<root>/predictions）。既定: reports/{YOSOU_NAME}")
        parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        workflow = DevelopmentPredictionWorkflow(args.root / "models", args.root / "predictions", args.db)
        forecast = workflow.run(args.race_id, PredictionTiming.parse(args.timing))
        return [self._horses(forecast), self._race(forecast), self._tickets(forecast)]

    def _horses(self, forecast: DevelopmentForecast) -> Table:
        table = forecast.horses.round(_ROUNDED_DIGITS)
        return Table(list(table.columns), table.values.tolist(),
                     title=f"{forecast.race_id}（{forecast.timing.label}）: 1頭ごとの予測（1着の確率の高い順）",
                     note="4コーナーの位置と上がりの速さは 0 が先頭・いちばん速い、1 が最後方・いちばん遅い。"
                          "☆ = 5位以下で単勝の期待値がいちばん高い馬（1.0 以上のときだけ）、注 = 印の無い馬で先頭の確率がいちばん高い馬。")

    def _race(self, forecast: DevelopmentForecast) -> Table:
        table = forecast.race.round(_ROUNDED_DIGITS)
        return Table(list(table.columns), table.values.tolist(), title="レースの予測（前半のペースと、前半・後半タイム）")

    def _tickets(self, forecast: DevelopmentForecast) -> Table:
        table: pd.DataFrame = forecast.tickets
        return Table(list(table.columns), table.values.tolist(), title="印どおりの買い目（1点 100円）",
                     note="馬番の決まっていない木曜は出さない。期待値で買う買い目は、確定オッズが要るので、年ごとの確かめだけで出す。")
