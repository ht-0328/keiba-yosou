"""血統（父・父の父・母父）ごとに、産駒の成績を条件別に出す。

**産駒の成績 = その血統を持つ馬たちが走った成績。** 種牡馬自身が現役だったころの成績ではない。
成績7つに加えて2つの差（その血統の全体との差・その条件の全馬との差）を出すので、
**その血統が得意な条件**と、**ほかの血統より強い条件**が分かる。

    uv run python tools/血統成績/pedigree.py --list                                  # 選べる立場・条件・並べ方
    uv run python tools/血統成績/pedigree.py --split 芝ダ --top 30                    # 父 × 芝ダ（複勝率の高い順）
    uv run python tools/血統成績/pedigree.py --split 距離帯 --sort 条件の平均との差 --top 30
    uv run python tools/血統成績/pedigree.py --name キタサンブラック --all             # その血統を全部の条件で
    uv run python tools/血統成績/pedigree.py --role 母父 --split 競馬場 --surface 芝
    uv run python tools/血統成績/pedigree.py --overall --top 50                       # 条件で分けない血統ごとの成績

条件どうしを比べるときは「条件の平均との差」で並べる。複勝率は頭数で変わるので、
「血統の全体との差」だけで見ると、頭数の少ない障害レースがいつも得意に見える（``--surface 芝`` で絞るのも手）。

出走の少ない血統は落とす（``--min-runs``、既定 50）。条件で分けたあとに残す出走数は ``--min-split-runs``（既定 20）。
対象は中央競馬の確定成績。取消・除外は出走に数えない。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, pedigree, perf  # noqa: E402

#: ``--all`` で並べて出す条件。
ALL_SPLITS: tuple[str, ...] = ("競馬場", "芝ダ", "馬場状態", "距離帯")
DEFAULT_ROLE = "父"
DEFAULT_SPLIT = "芝ダ"


def main(args) -> None:
    """一覧・全体・条件別のどれかを出す。"""
    if args.list:
        cli.emit(pedigree.catalog(), args)
        return
    filters = cli.filters_from(args)
    role_dim = pedigree.role(args.role)
    with db.open_db(args.db) as con:
        if args.overall:
            overall = pedigree.overall_rows(con, role_dim, filters, args.min_runs)
            cli.emit(pedigree.overall_table(overall, args.role, filters), args)
            return
        tables = [_split_table(con, args, role_dim, split_name, filters) for split_name in _split_names(args)]
    cli.emit(tables, args)


def _split_names(args) -> tuple[str, ...]:
    """出す条件の名前。``--all`` なら4つ並べる。"""
    return ALL_SPLITS if args.all else (args.split,)


def _split_table(con, args, role_dim, split_name: str, filters):
    """1つの条件についての表。"""
    split_dim = pedigree.split(split_name)
    rows = pedigree.split_rows(con, role_dim, split_dim, filters, min_runs=args.min_runs,
                               min_split_runs=args.min_split_runs, name=args.name)
    shown = pedigree.sorted_rows(rows, sort_key=args.sort, top=args.top)
    cover = perf.coverage(con, filters, split_dim)
    return pedigree.split_table(shown, args.role, split_dim, filters, cover)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=None)
    parser.add_argument("--list", action="store_true", help="選べる血統の立場・条件・並べ方の一覧を出して終わる")
    parser.add_argument("--role", default=DEFAULT_ROLE, choices=tuple(pedigree.ROLES),
                        help=f"血統の立場（既定: {DEFAULT_ROLE}）")
    parser.add_argument("--split", default=DEFAULT_SPLIT, choices=tuple(pedigree.SPLITS),
                        help=f"条件の切り口（既定: {DEFAULT_SPLIT}）")
    parser.add_argument("--all", action="store_true", help=f"条件を並べて出す（{'・'.join(ALL_SPLITS)}）")
    parser.add_argument("--name", default=None, help="この血統だけを出す（名前の部分一致）")
    parser.add_argument("--overall", action="store_true", help="条件で分けず、血統ごとの成績だけを出す")
    parser.add_argument("--sort", default=pedigree.DEFAULT_SORT_KEY, choices=pedigree.SORT_KEYS,
                        help=f"並べ方（既定: {pedigree.DEFAULT_SORT_KEY}）")
    parser.add_argument("--top", type=int, default=None, help="条件ごとに出す行数（既定: 全部）")
    parser.add_argument("--min-runs", type=int, default=pedigree.DEFAULT_MIN_RUNS,
                        help=f"産駒の出走数がこれ未満の血統を落とす（既定: {pedigree.DEFAULT_MIN_RUNS}）")
    parser.add_argument("--min-split-runs", type=int, default=pedigree.DEFAULT_MIN_SPLIT_RUNS,
                        help=f"条件で分けたあと、出走数がこれ未満の行を落とす（既定: {pedigree.DEFAULT_MIN_SPLIT_RUNS}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
