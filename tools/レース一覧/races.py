"""条件に合うレースの一覧（1行 = 1レース、新しい順）。rid が付くので、レース詳細にそのまま渡せる。

    uv run python tools/レース一覧/races.py --from 2026-09-06 --to 2026-09-07               # その週末の全レース
    uv run python tools/レース一覧/races.py --venue 中山 --surface 芝 --distance 1600 --condition 良 --limit 50
    uv run python tools/レース一覧/races.py --class G1 --from 2025-01-01
    uv run python tools/レース一覧/races.py --jockey ルメール --pop 1 --from 2026-01-01    # その騎手の馬が1番人気だったレース

馬の条件（人気・オッズ・騎手・性別 …）を付けると「その馬が出たレース」になる。中央・確定成績だけ。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, race  # noqa: E402


def main(args) -> None:
    filters = cli.filters_from(args)
    with db.open_db(args.db) as con:
        result = race.list_races(con, filters, limit=args.limit, offset=args.offset)
    cli.emit(result, args)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=200)
    parser.add_argument("--offset", type=int, default=0, help="この件数だけ飛ばす")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
