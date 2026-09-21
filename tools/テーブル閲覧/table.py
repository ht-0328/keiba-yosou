"""元DB の表を1つずつ見る。表の一覧、列の一覧、中身（開催日や 列=値 で絞る）。

    uv run python tools/テーブル閲覧/table.py --list                          # 表の一覧（行数・期間）
    uv run python tools/テーブル閲覧/table.py se --describe                   # se の列の一覧
    uv run python tools/テーブル閲覧/table.py ra --from 2026-09-06 --limit 5   # 開催日で絞って5行
    uv run python tools/テーブル閲覧/table.py se --where 競馬場コード=05 --where レース番号=11 --from 2026-09-06
    uv run python tools/テーブル閲覧/table.py se --columns 馬番,馬名,単勝人気順,確定着順 --from 2026-09-06 --limit 20
    uv run python tools/テーブル閲覧/table.py hr__単勝払戻 --format csv --out reports/tmp/tansho.csv

列名は JV-Data 仕様書の日本語のまま。値は文字列（桁のまま）で出る。1度に出す列は 60 まで（--column-offset で続きを見る）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import browse, cli, db  # noqa: E402
from 共通.filters import parse_date  # noqa: E402


def main(args) -> None:
    """一覧・列の一覧・中身のどれかを出す。"""
    with db.open_db(args.db) as con:
        browser = browse.TableBrowser(con)
        if args.list or not args.name:
            result = browse.tables_table(browser.list_tables(args.date_from, args.date_to))
        elif args.describe:
            result = browser.describe(args.name)
        else:
            columns = [c.strip() for c in args.columns.split(",")] if args.columns else None
            rows = browser.read(
                args.name, limit=args.limit, offset=args.offset, column_offset=args.column_offset, columns=columns,
                date_from=args.date_from, date_to=args.date_to, equals=browse.parse_equals(args.where),
                max_rows=browse.CLI_MAX_ROWS,
            )
            result = browse.rows_table(rows)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=50)
    parser.add_argument("name", nargs="?", help="表の名前（ra, se, hr__単勝払戻 …）。省略すると一覧")
    parser.add_argument("--list", action="store_true", help="表の一覧を出す")
    parser.add_argument("--describe", action="store_true", help="列の一覧（番号・列名・型）を出す")
    parser.add_argument("--columns", metavar="列,列", help="出す列をカンマ区切りで選ぶ")
    parser.add_argument("--where", action="append", default=[], metavar="列=値", help="この値の行だけ（複数可、等値だけ）")
    parser.add_argument("--offset", type=int, default=0, help="この行数だけ飛ばす")
    parser.add_argument("--column-offset", type=int, default=0, help="この列数だけ飛ばす（60列を超える表の続き）")
    parser.add_argument("--from", dest="date_from", type=parse_date, metavar="YYYY-MM-DD", help="開催日の開始（含む）")
    parser.add_argument("--to", dest="date_to", type=parse_date, metavar="YYYY-MM-DD", help="開催日の終了（含む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
