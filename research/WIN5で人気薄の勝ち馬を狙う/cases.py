"""WIN5で人気薄の勝ち馬を狙う: 事例を集める（研究「WIN5で人気薄の勝ち馬を狙う」の入口。段1）。

    uv run python research/WIN5で人気薄の勝ち馬を狙う/cases.py                       # 2019年以降の平地で 10番人気以下が勝った事例の表
    uv run python research/WIN5で人気薄の勝ち馬を狙う/cases.py --focus 2026-11-01      # 詳しく見る日を変える

出るもの（Git 対象外）: ``reports/WIN5で人気薄の勝ち馬を狙う/事例.md``（事例の数・分布・レースの側の型・馬の側の手がかりと型・
人気薄の中の並べ方・今のモデルの見方・結果側の様子・詳しく見る日・事例の一覧）、``WIN5の事例.csv``、``平地の事例.csv``。
元DB は jvdata-store の jvdata.duckdb（``--db`` か環境変数 YOSOU_DB）。読むだけ。1〜2分。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import cli, db  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.case_study import CaseStudy, CaseStudySettings  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.fold_win_predictions import DEFAULT_PREDICTIONS  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "WIN5で人気薄の勝ち馬を狙う"


def main(args: argparse.Namespace) -> None:
    settings = CaseStudySettings(date_from=args.date_from, focus_date=args.focus, predictions=args.predictions)
    with db.open_db(args.db, default=db.JRA) as con:
        path = CaseStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2019, 1, 1),
                        help="事例の最初の開催日（既定: 2019-01-01）")
    parser.add_argument("--focus", default="2026-11-08", help="詳しく見る WIN5 の日（既定: 2026-11-08）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help="今のモデルの区切りごとの当日の1着の予測の pkl")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
