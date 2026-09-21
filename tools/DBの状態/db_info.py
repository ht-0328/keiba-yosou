"""元DB の状態（大きさ・表の数・中央の確定成績の期間と件数・途中から入っている表・同期の記録）を出す。

    uv run python tools/DBの状態/db_info.py
    uv run python tools/DBの状態/db_info.py --tables                      # 全部の表の行数と期間も
    uv run python tools/DBの状態/db_info.py --tables --from 2026-09-01    # 期間内の行数も数える
    uv run python tools/DBの状態/db_info.py --time-facts                  # 事実表の行数と作成にかかる秒
    uv run python tools/DBの状態/db_info.py --format json

「今どこまで入っているか」「dm・tm はいつからか」を、SQL を書かずに確かめるための道具。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import browse, cli, db, facts  # noqa: E402
from 共通.filters import parse_date  # noqa: E402


def main(args) -> None:
    """状態の縦表と、``--tables`` なら表の一覧を出す。"""
    path = db.resolve_db(args.db)
    with db.open_db(path) as con:
        tables = [browse.status_table(browse.db_status(con, path)), browse.year_counts(con)]
        if args.time_facts:
            tables.append(facts.timing_table(con))
        if args.tables:
            infos = browse.TableBrowser(con).list_tables(args.date_from, args.date_to)
            tables.append(browse.tables_table(infos))
    cli.emit(tables, args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--tables", action="store_true", help="全部の表の行数と期間も出す")
    parser.add_argument("--time-facts", action="store_true", help="事実表（1行=1頭の出走）を作って行数と秒を出す")
    parser.add_argument("--from", dest="date_from", type=parse_date, metavar="YYYY-MM-DD",
                        help="期間内の行数を数える開始日（--tables と一緒に使う）")
    parser.add_argument("--to", dest="date_to", type=parse_date, metavar="YYYY-MM-DD", help="同じく終了日")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
