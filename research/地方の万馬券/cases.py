"""地方の万馬券: 事例を集める（研究「地方の万馬券」の入口。段1）。

    uv run python research/地方の万馬券/cases.py                       # 2024年以降・11頭以上・3連単 10万円以上のレースの事例の表
    uv run python research/地方の万馬券/cases.py --from 2022-01-01       # 期間を変える
    uv run python research/地方の万馬券/cases.py --middle 4-6            # 中穴を 4〜6番人気にして見る
    uv run python research/地方の万馬券/cases.py --min-heads 1           # 頭数で絞らない

出るもの（Git 対象外）: ``reports/地方の万馬券/事例.md``（配当の帯ごとのレース数・決着の型・崩れた人気馬と来た穴馬の事情・レースの条件・事例の一覧）、
``事例の馬.csv``（10万馬券以上のレースの出走馬と事情）、``事例のレース.csv``。
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
from 地方の万馬券.analysis.case_study import CaseStudy, CaseStudySettings  # noqa: E402
from 地方の万馬券.analysis.payout_band import PayoutBand  # noqa: E402
from 地方の万馬券.analysis.popularity_band import PopularityBand  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"


def main(args: argparse.Namespace) -> None:
    middle = Range.parse(args.middle)
    settings = CaseStudySettings(
        date_from=args.date_from, min_heads=args.min_heads,
        popularity=PopularityBand(int(middle.low), int(middle.high)),
        payout=PayoutBand(args.solid, args.big, args.huge), list_limit=args.limit,
    )
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = CaseStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2024, 1, 1), help="事例の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--min-heads", type=int, default=11, help="対象にする最少の頭数（既定: 11）")
    parser.add_argument("--middle", default="4-7", help="中穴の人気の範囲（既定: 4-7。人気馬はその下、大穴はその上）")
    parser.add_argument("--solid", type=int, default=10_000, help="中荒れの始まり（3連単の払戻、円。既定: 10000）")
    parser.add_argument("--big", type=int, default=100_000, help="大荒れの始まり（既定: 100000）")
    parser.add_argument("--huge", type=int, default=1_000_000, help="超荒れの始まり（既定: 1000000）")
    parser.add_argument("--limit", type=int, default=40, help="事例の一覧に出すレース数（既定: 40）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
