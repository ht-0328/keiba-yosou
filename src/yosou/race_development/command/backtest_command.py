"""backtest: 年ごとの的中率と回収率を確かめる。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from 共通 import render
from 共通.render import Table

from ..setting import BACKTEST_SETTINGS_PATH
from ..workflow import BacktestWorkflow
from .backtest_tables import BacktestTables
from .yosou_name import PROJECT_ROOT, YOSOU_NAME

#: 確かめる年の既定（設計書 15 の 18）。
DEFAULT_YEARS = "2020-2026"
#: 結果の表のファイルの名前（``reports/race_development/backtest/`` の下）。
RESULT_NAME = "results"


class BacktestCommand:
    """``backtest``: 各年を、その前の年までのデータだけで学習し直して当日の時点で予測し、券種ごと・年ごとの的中率と回収率を出す（設計書 16 の 7）。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "backtest", help="年ごとに学習し直して過去のレースを予測し、券種ごと・年ごとの的中率と回収率を出す", allow_abbrev=False,
        )
        parser.add_argument("--years", default=DEFAULT_YEARS,
                            help=f"確かめる年（例: 2020-2026 か 2024,2025。既定: {DEFAULT_YEARS}）")
        parser.add_argument("--config", type=Path, default=BACKTEST_SETTINGS_PATH,
                            help="ハイパーパラメータの設定ファイル（TOML。既定は setting/backtest_settings.toml。速さのために学習率を上げたもの）")
        parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "reports" / YOSOU_NAME,
                            help=f"途中の結果と表の置き場所（既定: reports/{YOSOU_NAME}。Git の対象外）")
        parser.add_argument("--reuse-datasets", action="store_true",
                            help="元DB が更新されていても、前に作った学習データを使う（表だけを作り直すとき。最新のレースが足されると、前の組の予測をすべて作り直すことになるため）")
        parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
        parser.add_argument("--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT, help="出力の形式（既定: markdown）")
        parser.add_argument("--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）")
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """結果の表は、``<root>/backtest/results.md`` にも書く。"""
        workflow = BacktestWorkflow(args.root, args.db, self._progress, args.reuse_datasets)
        report = workflow.run(self._years(args.years), args.config)
        tables = BacktestTables(report).tables()
        path = workflow.save_text(RESULT_NAME, render.render(tables, render.DEFAULT_FORMAT) + "\n")
        self._progress(f"結果の表を書いた: {path}")
        return tables

    def _years(self, text: str) -> list[int]:
        """``2020-2026`` か ``2024,2025`` の書き方から年の並びを作る。"""
        if "-" in text:
            first, last = (int(part) for part in text.split("-", 1))
            return list(range(first, last + 1))
        return [int(part) for part in text.split(",")]

    def _progress(self, message: str) -> None:
        """進み具合を、時刻を付けて標準エラーに出す（結果の表は標準出力なので混ざらない）。"""
        print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)
