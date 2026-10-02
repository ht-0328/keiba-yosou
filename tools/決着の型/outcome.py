"""レース単位の決着（3着以内の人気の組・人気の和・1番人気の着順 …）の割合と、人気で決める買い目の回収率を数える。

    uv run python tools/決着の型/outcome.py --list                                   # 決着の切り口の一覧
    uv run python tools/決着の型/outcome.py share top5-mix                           # 3着以内が「上位人気2頭+穴馬1頭」などになる割合
    uv run python tools/決着の型/outcome.py share top3-any year --venue 東京          # 切り口を2つ以上書くと組み合わせ（年ごと）
    uv run python tools/決着の型/outcome.py share fav-pair --under10 -3 --under30 -5  # WID-05 の条件のレースで 1・2番人気が2頭とも3着以内の割合
    uv run python tools/決着の型/outcome.py bet 3連複:1,2,3,5,6 --venue 東京          # 人気で決めるボックスの回収率（年ごと）
    uv run python tools/決着の型/outcome.py bet 3連単:2/1/6-10 --venue 新潟 --surface ダート --distance 1200   # フォーメーション
    uv run python tools/決着の型/outcome.py hasami                                   # ハサミ目（10R の 1〜3着 → 11R の単勝・複勝）
    uv run python tools/決着の型/outcome.py ratio                                    # 馬単の払戻 ÷ 馬連の払戻

対象は中央競馬の確定成績。人気・オッズは確定のもの。レースを選ぶ条件はレース単位の項目（競馬場・芝ダ・コース・距離・馬場・
クラス・頭数・期間・月）と、オッズの散らばり（--under10 --under30）・限定戦（--age-only）。
買い目は「券種:人気」で書く。列が1つならボックス、券種の馬の数と同じなら / で区切ったフォーメーション（1,3-5 のように範囲も書ける）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from 決着の型 import outcome_dimension  # noqa: E402
from 決着の型.hasami_bet import DEFAULT_SOURCE_RACE, DEFAULT_TARGET_RACE, HasamiBet  # noqa: E402
from 決着の型.outcome_share import OutcomeShare  # noqa: E402
from 決着の型.pattern_bet import PatternBet  # noqa: E402
from 決着の型.pattern_settlement import PatternSettlement  # noqa: E402
from 決着の型.payout_ratio import PayoutRatio  # noqa: E402
from 決着の型.popularity_map import PopularityMap  # noqa: E402
from 決着の型.race_selection import RaceSelection  # noqa: E402
from 決着の型.race_table import RaceTable  # noqa: E402
from 決着の型.repository.combo_payout_repository import ComboPayoutRepository  # noqa: E402
from 決着の型.repository.race_runner_repository import RaceRunnerRepository  # noqa: E402
from 決着の型.ticket_kind import ticket_kind  # noqa: E402

COMMANDS: dict[str, str] = {
    "share": "決着の切り口ごとのレース数と割合（切り口を1つ以上）",
    "bet": "人気で決める買い目（券種:人気）の回収率",
    "hasami": "ハサミ目の単勝・複勝の回収率",
    "ratio": "馬単の払戻 ÷ 馬連の払戻 の分布",
}


def main(args) -> None:
    if args.list:
        cli.emit(catalog(), args)
        return
    if not args.command:
        raise ValueError(f"何を数えるかを指定してください: {', '.join(COMMANDS)}（--list で切り口の一覧）")
    selection = RaceSelection.from_args(args)
    with db.open_db(args.db) as con:
        runners = RaceRunnerRepository(con).read(selection.filters)
        races = selection.apply(RaceTable().build(runners))
        runners = runners[runners["race_id"].isin(races.index)]
        if args.command == "share":
            result = OutcomeShare([outcome_dimension.dimension(name) for name in args.args]).table(races, selection.describe())
        elif args.command == "bet":
            result = _bet_tables(con, args.args, races, runners, selection)
        elif args.command == "hasami":
            result = HasamiBet(args.source, args.target).table(HasamiBet(args.source, args.target).settle(runners), selection.describe())
        elif args.command == "ratio":
            payouts = ComboPayoutRepository(con)
            ratio = PayoutRatio()
            ratios = ratio.ratios(races, payouts.read(ticket_kind("馬単"), selection.filters), payouts.read(ticket_kind("馬連"), selection.filters))
            result = ratio.table(ratios, selection.describe())
        else:
            raise ValueError(f"知らない集計です: {args.command}（{', '.join(COMMANDS)}）")
    cli.emit(result, args)


def _bet_tables(con, texts: list[str], races, runners, selection: RaceSelection) -> list[Table]:
    """買い目ごとに精算の表を作る（払戻は券種ごとに1回だけ読む）。"""
    if not texts:
        raise ValueError("買い目を 券種:人気 の形で1つ以上書いてください（例 3連複:1,2,3,5,6）")
    bets = [PatternBet.parse(text) for text in texts]
    popularity = PopularityMap(runners)
    payouts = ComboPayoutRepository(con)
    paid = {kind.name: payouts.read(kind, selection.filters) for kind in {bet.kind for bet in bets}}
    tables = []
    for bet in bets:
        settlement = PatternSettlement(bet)
        tables.append(settlement.table(settlement.settle(races, popularity, paid[bet.kind.name]), selection.describe()))
    return tables


def catalog() -> Table:
    """決着の切り口の一覧。"""
    rows = [[dim.name, dim.title, " / ".join(dim.labels), dim.note] for dim in outcome_dimension.DIMENSIONS.values()]
    return Table(["切り口", "表題", "値", "注意"], rows, title="決着の切り口の一覧")


def build_parser():
    parser = cli.build_parser(__doc__, filters=False, limit=None)
    parser.add_argument("command", nargs="?", choices=list(COMMANDS), help="何を数えるか: " + "、".join(f"{k} = {v}" for k, v in COMMANDS.items()))
    parser.add_argument("args", nargs="*", help="share なら切り口の名前（1つ以上）、bet なら買い目（券種:人気。1つ以上）")
    parser.add_argument("--list", action="store_true", help="決着の切り口の一覧を出して終わる")
    parser.add_argument("--source", type=int, default=DEFAULT_SOURCE_RACE, help=f"hasami: 1〜3着を見る前のレース番号（既定 {DEFAULT_SOURCE_RACE}）")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_RACE, help=f"hasami: 買う次のレース番号（既定 {DEFAULT_TARGET_RACE}）")
    RaceSelection.add_arguments(parser)
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
