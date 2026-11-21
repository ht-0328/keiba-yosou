"""高知ファイナルの高配当: 事例を集める（研究「高知ファイナルの高配当」の入口。段1）。

    uv run python research/高知ファイナルの高配当/cases.py                      # 9頭以上のファイナルレースの配当の帯・決着の型と、2024年以降の荒れた 20 レースの事例
    uv run python research/高知ファイナルの高配当/cases.py --list-from 2022-01-01 --limit 40   # 並べる事例の期間と数を変える
    uv run python research/高知ファイナルの高配当/cases.py --middle 4-6          # 中穴を 4〜6番人気にして見る

出るもの（Git 対象外）: ``reports/高知ファイナルの高配当/事例.md``（配当の帯ごとのレース数・決着の型・荒れたレースの出走馬ごとの人気・オッズ・着順・近走）。
元DB は nvdata-store の nvdata.duckdb（``--db`` か環境変数 YOSOU_LOCAL_DB）。読むだけ。
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
from 共通.filters import Range  # noqa: E402
from 地方の万馬券.analysis.payout_band import PayoutBand  # noqa: E402
from 高知ファイナルの高配当.analysis.case_study import CaseStudy, CaseStudySettings  # noqa: E402
from 高知ファイナルの高配当.analysis.popularity_band import PopularityBand  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "高知ファイナルの高配当"


def main(args: argparse.Namespace) -> None:
    middle = Range.parse(args.middle)
    settings = CaseStudySettings(
        min_heads=args.min_heads, popularity=PopularityBand(int(middle.low), int(middle.high)),
        payout=PayoutBand(args.solid, args.big, args.huge), list_from=args.list_from, list_limit=args.limit,
    )
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = CaseStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--min-heads", type=int, default=9, help="対象にする最少の頭数（既定: 9）")
    parser.add_argument("--middle", default="4-7", help="中穴の人気の範囲（既定: 4-7。人気馬はその下、大穴はその上）")
    parser.add_argument("--solid", type=int, default=10_000, help="中荒れの始まり（3連単の払戻、円。既定: 10000）")
    parser.add_argument("--big", type=int, default=100_000, help="大荒れの始まり（既定: 100000）")
    parser.add_argument("--huge", type=int, default=1_000_000, help="超荒れの始まり（既定: 1000000）")
    parser.add_argument("--list-from", type=date.fromisoformat, default=date(2024, 1, 1), help="1レースずつ並べる事例の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--limit", type=int, default=20, help="1レースずつ並べる事例の数（既定: 20）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
