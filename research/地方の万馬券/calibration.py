"""地方の万馬券: 組の確率の直し（研究「地方の万馬券」の入口。段3 の補足）。

    uv run python research/地方の万馬券/calibration.py --test-from 2024-01-01 --predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証 --fit-year 2024
                                                            # 2024年で直しを当てはめ、2024〜2026年で直した期待値の買い目の成績

全部の組に 予想の組の確率（Harville）・市場の組の確率（券種の確定オッズ）・的中 を付け、
「的中 ~ log(予想の確率) + log(市場の確率)」のロジスティック回帰を最初の年で当てはめる。係数が「予想の確率がどれだけ当てになるか」を表し、
直した期待値（直した確率 × オッズ）が 1 以上の組がどれだけ残るかで、その券種に買える組があるかが分かる。
出るもの（Git 対象外）: ``reports/地方の万馬券/組の確率の直し.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

from 共通 import cli, db  # noqa: E402
from 地方の万馬券.analysis.trifecta.calibration_study import CalibrationStudy, CalibrationStudySettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"
DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"


def main(args: argparse.Namespace) -> None:
    settings = CalibrationStudySettings(test_from=args.test_from, predictions=args.predictions, fit_year=args.fit_year,
                                        max_points=args.max_points, min_heads=args.min_heads, report_name=args.report_name)
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = CalibrationStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help="全頭の予想の予測の表の置き場所（対象の期間を全部含むもの）")
    parser.add_argument("--fit-year", type=int, default=2024, help="直しを当てはめる年（既定: 2024。ほかの年で確かめる）")
    parser.add_argument("--max-points", type=int, default=30, help="買うときの 1レースの点数の上限（既定: 30）")
    parser.add_argument("--min-heads", type=int, default=11, help="対象にする最少の頭数（既定: 11）")
    parser.add_argument("--report-name", default="組の確率の直し", help="書く Markdown の名前（既定: 組の確率の直し）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
