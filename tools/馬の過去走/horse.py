"""馬名か血統登録番号（hid）から、馬のプロフィールと中央の過去走（新しい順）を出す。

    uv run python tools/馬の過去走/horse.py ウマノナマエ                      # 馬名（部分一致。複数なら候補の表）
    uv run python tools/馬の過去走/horse.py 2021100001                        # hid（10桁）
    uv run python tools/馬の過去走/horse.py 2021100001 --before 2026-09-06    # その日より前の出走だけ（前走の材料を見るとき）
    uv run python tools/馬の過去走/horse.py 2021100001 --limit 10 --format csv --out reports/tmp/horse.csv

候補が複数のときは hid を指定し直す。過去走は中央のレースだけ（地方・海外は入っていない）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, horse, keys  # noqa: E402


def looks_like_hid(text: str) -> bool:
    return len(text.strip()) == keys.HID_LENGTH and text.strip().isdigit()


def main(args) -> None:
    with db.open_db(args.db) as con:
        if looks_like_hid(args.target):
            hid = args.target.strip()
        else:
            found = horse.find_horses(con, args.target, limit=args.limit)
            if len(found.rows) != 1:
                cli.emit(found, args)
                return
            hid = found.rows[0][0]
        profile = horse.horse_profile(con, hid)
        runs = horse.horse_runs(con, hid, limit=args.limit, before=args.before)
    cli.emit([horse.profile_table(profile), runs], args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=50)
    parser.add_argument("target", help="馬名（部分一致）か hid（10桁）")
    parser.add_argument("--before", metavar="YYYY-MM-DD", help="この日より前の出走だけを出す")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
