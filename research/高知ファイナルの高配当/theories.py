"""高知ファイナルの高配当: 理論を全レースで確かめる（研究「高知ファイナルの高配当」の入口。段2）。

    uv run python research/高知ファイナルの高配当/theories.py                  # 9頭以上のファイナルレース全部。理論ごとに同じ人気の馬と比べる
    uv run python research/高知ファイナルの高配当/theories.py --min-heads 11   # 頭数の線を変える
    uv run python research/高知ファイナルの高配当/theories.py --split 2021-01-01 2025-01-01   # 期間の区切りを変える

出るもの（Git 対象外）: ``reports/高知ファイナルの高配当/理論の検証.md``（理論①〜⑤・差が無かった材料・そのほかに確かめた材料）、``理論の検証.csv``。
理論の一覧は ``analysis/theory_catalog.py``。元DB は nvdata-store の nvdata.duckdb（``--db`` か環境変数 YOSOU_LOCAL_DB）。読むだけ。
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
from 高知ファイナルの高配当.analysis.period_split import PeriodSplit  # noqa: E402
from 高知ファイナルの高配当.analysis.popularity_band import PopularityBand  # noqa: E402
from 高知ファイナルの高配当.analysis.theory_study import TheoryStudy, TheoryStudySettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "高知ファイナルの高配当"
_DEFAULT_SPLIT = PeriodSplit().boundaries


def main(args: argparse.Namespace) -> None:
    middle = Range.parse(args.middle)
    settings = TheoryStudySettings(
        min_heads=args.min_heads, popularity=PopularityBand(int(middle.low), int(middle.high)),
        periods=PeriodSplit(tuple(sorted(args.split))), min_runs=args.min_runs,
    )
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = TheoryStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--min-heads", type=int, default=9, help="対象にする最少の頭数（既定: 9）")
    parser.add_argument("--middle", default="4-7", help="中穴の人気の範囲（既定: 4-7。人気馬はその下、大穴はその上）")
    parser.add_argument("--split", type=date.fromisoformat, nargs="+", default=list(_DEFAULT_SPLIT),
                        help="期間の区切りの日（既定: 2020-01-01 2024-01-01 の3期間）")
    parser.add_argument("--min-runs", type=int, default=60, help="表に出す最少の頭数（既定: 60）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
