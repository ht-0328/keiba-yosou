"""成績7つ（着別度数・勝率・連対率・複勝率・馬券外率・単勝回収率・複勝回収率）を、切り口ごとに数える。

    uv run python tools/成績集計/perf.py --list                       # 切り口の一覧
    uv run python tools/成績集計/perf.py popularity --venue 東京 --course 芝・左 --distance 1600 --condition 良
    uv run python tools/成績集計/perf.py jockey --venue 京都 --surface 芝 --distance 2000 --rank-by 複勝率 --top 10
    uv run python tools/成績集計/perf.py odds --pop 1                  # 1番人気をオッズ帯で分ける
    uv run python tools/成績集計/perf.py class --by-popularity          # クラス×人気
    uv run python tools/成績集計/perf.py course --pop 1 --min-runs 30   # コース単位（競馬場×コース×距離×馬場状態）の1番人気
    uv run python tools/成績集計/perf.py popularity-top --cross tm-top --venue 中山
    uv run python tools/成績集計/perf.py --check                       # reports/stats の値と答え合わせ

出力は reports/stats と同じ9列（切り口 | 出走数 | 着別度数 | 勝率 | 連対率 | 複勝率 | 馬券外率 | 単勝回収率 | 複勝回収率）。
取消・除外は出走に数えない。競走中止・失格は「出走して馬券外」。回収率の基準は 80%（控除率 20%）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, perf  # noqa: E402
from 成績集計 import check  # noqa: E402


def chosen_dimension(args) -> perf.Dimension:
    """位置引数と --cross / --by-popularity から切り口を組み立てる。"""
    dim = perf.dimension(args.dimension)
    if args.cross:
        dim = perf.cross(dim, *(perf.dimension(name) for name in args.cross))
    if args.by_popularity:
        dim = perf.by_popularity(dim)
    return dim


def main(args) -> None:
    """一覧・答え合わせ・集計のどれかを出す。"""
    if args.list:
        cli.emit(perf.catalog(), args)
        return
    if args.check:
        with db.open_db(args.db) as con:
            result = check.run_check(con, date_from=args.filter_from or check.CHECK_DATE_FROM,
                                     date_to=args.filter_to or check.CHECK_DATE_TO)
        cli.emit(check.check_table(result), args)
        if not result.ok:
            raise SystemExit(cli.EXIT_ERROR)
        return
    if not args.dimension:
        raise ValueError("切り口を指定してください（--list で一覧）")
    dim = chosen_dimension(args)
    filters = cli.filters_from(args)
    with db.open_db(args.db) as con:
        rows = perf.perf_rows(con, dim, filters, top=args.top, min_runs=args.min_runs, rank_by=args.rank_by)
        cover = perf.coverage(con, filters, dim)
    cli.emit(perf.perf_table(rows, dim, filters, cover), args)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=None)
    parser.add_argument("dimension", nargs="?", help="切り口の名前（--list で一覧）")
    parser.add_argument("--list", action="store_true", help="切り口の一覧を出して終わる")
    parser.add_argument("--check", action="store_true", help="reports/stats の東京 芝・左 1600m 良 の1番人気と答え合わせ")
    parser.add_argument("--top", type=int, default=None, help="順位を付ける切り口（騎手・血統・馬）で出す件数（既定: 全部）")
    parser.add_argument("--min-runs", type=int, default=None, help="出走数がこれ未満の行を落とす（既定: 切り口ごと）")
    parser.add_argument("--rank-by", choices=perf.RANK_KEYS, default=perf.DEFAULT_RANK_KEY, help="順位を付ける列（既定: 勝率）")
    parser.add_argument("--by-popularity", action="store_true", help="切り口の値×単勝人気で分ける")
    parser.add_argument("--cross", action="append", default=[], metavar="切り口", help="切り口を組み合わせる（何度でも）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
