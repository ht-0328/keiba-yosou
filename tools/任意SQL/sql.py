"""元DB に、読むだけの SQL を1文流して表にする。

    uv run python tools/任意SQL/sql.py "select count(*) from ra"
    uv run python tools/任意SQL/sql.py "select 馬番, 馬名, 単勝人気順 from se where 開催年='2026' and 開催月日='0906' and 競馬場コード='05' and レース番号='11' order by 馬番"
    uv run python tools/任意SQL/sql.py --file reports/tmp/q.sql --limit 1000 --format csv --out reports/tmp/q.csv
    echo "describe se" | uv run python tools/任意SQL/sql.py

接続は読み取り専用。SELECT / WITH / FROM / DESCRIBE / SHOW / SUMMARIZE / EXPLAIN / PRAGMA だけ通り、
結果は --limit 行で切る。--timeout 秒（既定 60）を越えたら止める。
列名は日本語のままなので、角括弧を含む列（"開催回[第N回]"）は二重引用符で包む。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import browse, cli, db  # noqa: E402


def read_sql(args) -> str:
    """引数・ファイル・標準入力の順に SQL を探す。"""
    if args.sql:
        return args.sql
    if args.file:
        return args.file.read_text(encoding="utf-8")
    text = sys.stdin.read()
    if not text.strip():
        raise ValueError("SQL を引数か --file か標準入力で渡してください")
    return text


def main(args) -> None:
    """SQL を1文実行して出す。"""
    sql = read_sql(args)
    with db.open_db(args.db) as con:
        result = browse.run_sql(con, sql, limit=args.limit, timeout_s=args.timeout)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=200)
    parser.add_argument("sql", nargs="?", help="SQL（1文）。省略すると --file か標準入力")
    parser.add_argument("--file", type=Path, help="SQL を書いたファイル（UTF-8）")
    parser.add_argument("--timeout", type=float, default=browse.DEFAULT_TIMEOUT_SECONDS, help="この秒数を越えたら止める")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
