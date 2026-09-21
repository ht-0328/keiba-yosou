"""1レースの詳細: 見出し（コース・距離・馬場・頭数・発走）、出走表と結果、ラップ、通過順、払戻。

    uv run python tools/レース詳細/race.py 2026090606040211                  # rid で
    uv run python tools/レース詳細/race.py --date 2026-09-06 --venue 中山 --race 11
    uv run python tools/レース詳細/race.py --date 2026-09-06 --venue 06 --race 11 --format json

事象を1件ずつ見る（なぜ人気馬が負けたか）ときの道具。確定前の出馬表（データ区分 1・2）でも見られる。
出走表の hid を 馬の過去走 に渡すと、その馬の前走が見られる。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, race  # noqa: E402


def main(args) -> None:
    if not args.rid and not (args.date and args.venue and args.race):
        raise ValueError("rid か、--date --venue --race の3つを指定してください")
    with db.open_db(args.db) as con:
        rid = args.rid or race.resolve_rid(con, args.date, args.venue, args.race)
        detail = race.race_detail(con, rid)
    cli.emit(detail.tables(), args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（rid を省くとき）")
    parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
    parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
