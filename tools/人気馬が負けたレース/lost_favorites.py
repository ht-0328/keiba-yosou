"""人気馬が負けた出走（1行 = 1頭）を集める。危険な人気馬の研究で、事象が起きたレースを集める起点。

    uv run python tools/人気馬が負けたレース/lost_favorites.py --from 2025-01-01                 # 1番人気が馬券外（既定）
    uv run python tools/人気馬が負けたレース/lost_favorites.py --pop 1-3 --finish 2- --venue 東京   # 1〜3番人気が勝てなかった
    uv run python tools/人気馬が負けたレース/lost_favorites.py --odds -1.9 --course 芝・左 --distance 1600 --condition 良
    uv run python tools/人気馬が負けたレース/lost_favorites.py --format csv --out reports/favorite-risk/lost.csv --limit 1000

対象（分母）は --pop（既定 1）と --odds で決め、事象（分子）は --finish（既定 4- = 4着以下。競走中止・失格も含む）で決める。
見出しに「対象 N 頭のうち M 頭（率）」が出る。各行に勝ち馬と rid・hid が付くので、レース詳細・馬の過去走に渡せる。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, events  # noqa: E402

KIND = "lost"


#: このツールでは --pop --odds が対象（分母）、--finish が事象（分子）。絞り込みとしては使わない。
RULE_FLAGS = ("pop", "odds", "finish")
FILTER_HELP = {
    "pop": "対象にする人気（既定 1）", "odds": "対象にする単勝オッズ（省略可）",
    "finish": "事象にする着順（既定 4- = 馬券外。競走中止・失格を含む。2- なら勝てなかった）",
}


def main(args) -> None:
    rule = events.rule_from(KIND, pop=cli.filter_value(args, "pop"), odds=cli.filter_value(args, "odds"),
                            finish=cli.filter_value(args, "finish"))
    filters = cli.filters_from(args, exclude=RULE_FLAGS)
    with db.open_db(args.db) as con:
        result = events.search_events(con, rule, filters, limit=args.limit, offset=args.offset)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=200, filter_help=FILTER_HELP)
    parser.add_argument("--offset", type=int, default=0, help="この件数だけ飛ばす")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
