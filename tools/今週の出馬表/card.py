"""今週の出馬表: これから走るレースの一覧と、1レースの出馬表（レース前に分かる材料と各馬の近走）。

    uv run python tools/今週の出馬表/card.py                                          # 今日以降のレースの一覧
    uv run python tools/今週の出馬表/card.py --date 2026-09-19 --venue 中山            # その日・その競馬場の一覧
    uv run python tools/今週の出馬表/card.py --date 2026-09-19 --venue 中山 --race 11  # 1レースの出馬表と各馬の近走
    uv run python tools/今週の出馬表/card.py 2026091906040511 --runs 3                # rid で。近走は3走まで
    uv run python tools/今週の出馬表/card.py --date 2026-09-19 --venue 中山 --all --out reports/cards/0919-中山.md

確定前（木曜の出走馬名表・金土の出馬表）のレースを見る道具。出走馬名表の間は枠番・馬番が空。
近走・通算は中央の確定成績の「その開催日より前」だけ。結果（着順・払戻）は レース詳細 で見る。
過去の日付も ``--date`` か ``--from --to`` で見られる。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, db, race  # noqa: E402


def main(args) -> None:
    with db.open_db(args.db) as con:
        if args.rid or args.race:
            result = _one_card(con, args)
        else:
            result = _race_list_or_all_cards(con, args)
    cli.emit(result, args)


def _one_card(con, args):
    if not args.rid and not (args.date and args.venue):
        raise ValueError("1レースを見るには rid か、--date --venue --race の3つを指定してください")
    rid = args.rid or race.resolve_rid(con, args.date, args.venue, args.race)
    return card.race_card(con, rid, runs=args.runs).tables()


def _race_list_or_all_cards(con, args):
    date_from = args.date or args.date_from or date.today().isoformat()
    date_to = args.date or args.date_to
    races = card.list_cards(con, date_from=date_from, date_to=date_to, venue=args.venue, limit=args.limit)
    if not args.all:
        return races
    rid_column = races.columns.index("rid")
    return [table for row in races.rows for table in card.race_card(con, row[rid_column], runs=args.runs).tables()]


def build_parser():
    parser = cli.build_parser(__doc__, limit=card.DEFAULT_LIST_LIMIT)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）。指定するとそのレースの出馬表")
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（その1日だけ）")
    parser.add_argument("--from", dest="date_from", help="開催日の開始（省略すると今日）")
    parser.add_argument("--to", dest="date_to", help="開催日の終了（省略すると DB にある最後まで）")
    parser.add_argument("--venue", help="競馬場の名前かコード")
    parser.add_argument("--race", type=int, help="レース番号。--date --venue と合わせて1レースの出馬表")
    parser.add_argument("--runs", type=int, default=card.DEFAULT_RUNS,
                        help=f"各馬の近走を何走まで出すか（既定: {card.DEFAULT_RUNS}、0 で出さない）")
    parser.add_argument("--all", action="store_true", help="一覧ではなく、条件に合う全レースの出馬表を続けて出す")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
