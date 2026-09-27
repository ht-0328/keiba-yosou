"""能力指数: 出走馬ごとに、過去の走破タイムから作った能力の数字を出し、高い順に並べる。

    uv run python tools/能力指数/ability.py --date 2026-09-27 --venue 中山 --race 11          # 1レースのランキング
    uv run python tools/能力指数/ability.py --date 2026-09-27 --venue 中山 --race 11 --detail # 各馬の近5走のスピード指数も出す
    uv run python tools/能力指数/ability.py --date 2026-09-27 --venue 中山 --race 11 --condition 稍重  # 発表前の馬場状態を与える
    uv run python tools/能力指数/ability.py --date 2026-09-27 --all --out reports/能力指数/0927.md    # その日の全レース
    uv run python tools/能力指数/ability.py 2026092706040611                                     # rid で

能力指数 = 近8走（2年以内）のスピード指数を、新しい走ほど・今回の条件（距離・競馬場・芝ダと馬場）に近い走ほど重く見た平均。
スピード指数 = 走破タイムを、コースの基準タイム・その日の馬場差・斤量・ペース（展開の得・損）で補正した点数
（80 が1勝クラスの古馬のふつうの走。10点 = 1%速い）。着順・人気・オッズは使わない。
作り方と、候補を比べて決めた経緯は ``research/能力指数の作り方/``。
初回と、DB に新しい確定成績が入ったあとは、過去の全部の走の指数を作り直す（1〜2分）。作ったものは ``reports/能力指数/cache/`` にとっておく。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, codes, db, race  # noqa: E402
from 共通.ability import AbilitySettings, AbilityTables, FigureCache, RaceAbility  # noqa: E402
from 共通.ability.figure_cache import DEFAULT_FOLDER  # noqa: E402


def main(args) -> None:
    condition = codes.condition_code(args.condition) if args.condition else None
    settings = AbilitySettings()
    cache = FigureCache(settings, args.cache)
    tables = AbilityTables()
    with db.open_db(args.db) as con:
        if args.rebuild:
            print("過去の全部の走のスピード指数を作り直しています …", file=sys.stderr, flush=True)
            cache.load(con, rebuild=True)
        rids = _rids(con, args)
        ability = RaceAbility(settings, cache)
        results = []
        for rid in rids:
            report = ability.rank(con, rid, condition)
            results.append(tables.ranking(report))
            if args.detail:
                results.append(tables.history(report))
    cli.emit(results, args)


def _rids(con, args) -> list[str]:
    if args.all:
        if not args.date or args.rid or args.race:
            raise ValueError("--all は --date（と --venue）と合わせて使います")
        cards = card.list_cards(con, date_from=args.date, date_to=args.date, venue=args.venue)
        if not cards.rows:
            raise LookupError(f"{args.date} のレースが DB にありません")
        rid_at = cards.columns.index("rid")
        return [row[rid_at] for row in cards.rows]
    if args.rid:
        return [args.rid]
    if args.date and args.venue and args.race:
        return [race.resolve_rid(con, args.date, args.venue, args.race)]
    raise ValueError("レースを rid か、--date --venue --race の3つで指定してください（その日の全部なら --date --all）")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日 YYYY-MM-DD")
    parser.add_argument("--venue", help="競馬場の名前かコード")
    parser.add_argument("--race", type=int, help="レース番号")
    parser.add_argument("--all", action="store_true", help="--date（と --venue）の全レース")
    parser.add_argument("--condition", help="当日の馬場状態（良 / 稍重 / 重 / 不良）。発表前のレースで、馬場の適性に使う")
    parser.add_argument("--detail", action="store_true", help="各馬の近5走のスピード指数も出す")
    parser.add_argument("--rebuild", action="store_true", help="過去の全部の走のスピード指数を、必ず作り直す")
    parser.add_argument("--cache", type=Path, default=DEFAULT_FOLDER, help="過去の走の指数をとっておく場所（既定: reports/能力指数/cache）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
