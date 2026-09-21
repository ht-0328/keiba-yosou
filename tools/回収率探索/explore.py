"""指定した条件の中で、単勝か複勝の回収率が 100%（--threshold）を超える切り口の値を探す。

    uv run python tools/回収率探索/explore.py --venue 東京 --course 芝・左 --distance 1600 --condition 良
    uv run python tools/回収率探索/explore.py --pop 1 --min-runs 50 --target place            # 1番人気の中で複勝が 100% 以上
    uv run python tools/回収率探索/explore.py --venue 中山 --dimensions popularity,odds,frame,prev-finish --pairs
    uv run python tools/回収率探索/explore.py --list                                          # 使える切り口
    uv run python tools/回収率探索/explore.py --surface ダート --threshold 120 --top 30 --format csv --out reports/tmp/explore.csv

条件（絞り込み）を固定し、切り口（人気・オッズ帯・枠・前走の着順・逃げ経験・持ち時計順位 …）を1つずつ当てて、
出走数が --min-runs（既定 30）以上で回収率が閾値以上の行を、回収率の高い順に並べる。年ごとの回収率も添える。
出走数の少ない行は偶然で超えやすい。年ごとに揃っている条件を優先し、別の期間（--from/--to）でも確かめてから使う。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, explore  # noqa: E402


def main(args) -> None:
    if args.list:
        cli.emit(explore.catalog(), args)
        return
    names = [name for name in args.dimensions.split(",")] if args.dimensions else None
    filters = cli.filters_from(args)
    with db.open_db(args.db) as con:
        result = explore.explore(con, filters, names, min_runs=args.min_runs, threshold=args.threshold / 100,
                                 target=args.target, pairs=args.pairs, top=args.top)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=None)
    parser.add_argument("--dimensions", metavar="a,b,c", help="試す切り口（カンマ区切り。既定は --list の○）")
    parser.add_argument("--list", action="store_true", help="使える切り口の一覧を出して終わる")
    parser.add_argument("--min-runs", type=int, default=explore.DEFAULT_MIN_RUNS, help=f"出走数がこれ未満の行は見ない（既定 {explore.DEFAULT_MIN_RUNS}）")
    parser.add_argument("--threshold", type=float, default=explore.DEFAULT_THRESHOLD * 100, help="回収率の閾値（%%。既定 100）")
    parser.add_argument("--target", choices=list(explore.TARGETS), default=explore.DEFAULT_TARGET, help="単勝か複勝か両方か（既定 both）")
    parser.add_argument("--pairs", action="store_true", help=f"2つの切り口の組み合わせも試す（切り口 {explore.MAX_PAIR_DIMENSIONS} 個まで）")
    parser.add_argument("--top", type=int, default=explore.DEFAULT_TOP, help=f"出す行数（既定 {explore.DEFAULT_TOP}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
