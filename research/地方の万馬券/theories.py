"""地方の万馬券: 理論を全レースで確かめる（研究「地方の万馬券」の入口。段2）。

    uv run python research/地方の万馬券/theories.py                     # 2019年以降・11頭以上。2024年の前後の2つの期間で、理論ごとに同じ人気の馬全体と比べる
    uv run python research/地方の万馬券/theories.py --middle 4-6        # 中穴を 4〜6番人気にして比べる
    uv run python research/地方の万馬券/theories.py --from 2021-01-01 --split 2025-01-01

出るもの（Git 対象外）: ``reports/地方の万馬券/理論の検証.md``（人気馬の理論・穴馬の理論・荒れやすいレースの条件）、``理論の検証.csv``。
理論の一覧は ``analysis/theory_catalog.py``。元DB は nvdata-store の nvdata.duckdb（読むだけ）。
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
from 地方の万馬券.analysis.popularity_band import PopularityBand  # noqa: E402
from 地方の万馬券.analysis.theory_study import TheoryStudy, TheoryStudySettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"


def main(args: argparse.Namespace) -> None:
    middle = Range.parse(args.middle)
    settings = TheoryStudySettings(date_from=args.date_from, split=args.split, min_heads=args.min_heads,
                                   popularity=PopularityBand(int(middle.low), int(middle.high)))
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = TheoryStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2019, 1, 1), help="最初の開催日（既定: 2019-01-01）")
    parser.add_argument("--split", type=date.fromisoformat, default=date(2024, 1, 1), help="2つの期間の区切り（既定: 2024-01-01）")
    parser.add_argument("--min-heads", type=int, default=11, help="対象にする最少の頭数（既定: 11）")
    parser.add_argument("--middle", default="4-7", help="中穴の人気の範囲（既定: 4-7）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
