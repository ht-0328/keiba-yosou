"""穴馬が勝った（または馬券内に来た）出走を集める。人気馬が負けたとき「誰に負けたか」を見る道具。

    uv run python tools/穴馬が勝ったレース/longshot_wins.py --from 2025-01-01              # 単勝 10 倍以上が1着（既定）
    uv run python tools/穴馬が勝ったレース/longshot_wins.py --odds 20- --finish 1-3          # 20 倍以上が馬券内
    uv run python tools/穴馬が勝ったレース/longshot_wins.py --pop 8- --venue 中山 --surface ダート  # 8番人気以下が1着
    uv run python tools/穴馬が勝ったレース/longshot_wins.py --pop 6- --odds 15- --class 未勝利     # 両方（AND）

対象（分母）は --odds（既定 10-）か --pop で決め、どちらかを書けばそれだけが効く（両方書けば AND）。
事象（分子）は --finish（既定 1）。各行に1番人気の馬と着順・単勝払戻が付く。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, events  # noqa: E402

KIND = "longshot"


#: このツールでは --pop --odds が対象（分母）、--finish が事象（分子）。絞り込みとしては使わない。
RULE_FLAGS = ("pop", "odds", "finish")
FILTER_HELP = {
    "pop": "対象にする人気（例 8-。書いた方だけ効く）", "odds": "対象にする単勝オッズ（既定 10-。書いた方だけ効く）",
    "finish": "事象にする着順（既定 1 = 1着。1-3 なら馬券内）",
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
