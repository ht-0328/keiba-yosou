"""条件を組み合わせて出走（1行 = 1頭）を検索する。

    uv run python tools/出走検索/runners.py --venue 東京 --pop 1 --from 2026-01-01 --limit 20
    uv run python tools/出走検索/runners.py --course 芝・左 --distance 1600 --condition 良 --odds 1.0-1.9 --sort odds
    uv run python tools/出走検索/runners.py --jockey ルメール --class G1 --format csv --out reports/tmp/runners.csv
    uv run python tools/出走検索/runners.py --columns        # 事実表の列の一覧（意味つき）

絞り込みの項目は --help に全部ある。画面の「出走（検索）」と同じ条件・同じ結果。
取消・除外の馬は数えない。結果には rid（レース）と hid（馬）が付くので、レース詳細・馬の過去走にそのまま渡せる。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, facts, runners  # noqa: E402


def main(args) -> None:
    """絞り込みで検索して出す。"""
    if args.columns:
        cli.emit(facts.columns_table(), args)
        return
    filters = cli.filters_from(args)
    with db.open_db(args.db) as con:
        result = runners.search_runners(con, filters, limit=args.limit, offset=args.offset, sort=args.sort)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=200)
    parser.add_argument("--sort", choices=list(runners.SORTS), default=runners.DEFAULT_SORT, help="並べ替え（既定: date = 新しい順）")
    parser.add_argument("--offset", type=int, default=0, help="この件数だけ飛ばす")
    parser.add_argument("--columns", action="store_true", help="事実表の列の一覧を出して終わる")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
