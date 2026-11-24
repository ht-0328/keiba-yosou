"""地方の直前の買い目: 過去のレースでの成績を、時間の順を守って確かめる（3か月ごとに、それより前のレースだけで学び直す）。

    uv run python tools/地方の直前の買い目/check.py                       # 単勝・馬単・3連単（1着固定）の期間ごとの回収率と、期待度ごとの成績（10〜15分）
    uv run python tools/地方の直前の買い目/check.py --likeness 0.3 --payback 1.0

払戻は確定の値（元DB の払戻の表）。買う馬は学習用の表の断面（締め切りの約10分前）のオッズと予想だけで決める。
2つめの表は、全レースを地方の期待度（線への近さの S・A・B・C。設計書「買うレースと買い目を決める」の 11）で分けた、線にいちばん近い馬の単勝の成績。
結果は標準出力と reports/地方の直前の買い目/check.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli, db, render  # noqa: E402

from yosou.shared.race_grade import LocalExpectationScale  # noqa: E402

from 地方の直前の買い目.late_columns import RACE_DATE, RACE_ID  # noqa: E402
from 地方の直前の買い目.late_grade_table import LateGradeTable  # noqa: E402
from 地方の直前の買い目.late_rule import EXACTA_OPPONENTS, LIKENESS_LINE, OPPONENTS, PAYBACK_LINE, LateRule  # noqa: E402
from 地方の直前の買い目.late_settlement import LateSettlement  # noqa: E402
from 地方の直前の買い目.late_summary import LateSummary  # noqa: E402
from 地方の直前の買い目.late_training_table import DEFAULT_PATH, LateTrainingTable  # noqa: E402
from 地方の直前の買い目.late_walk_forward import LateWalkForward  # noqa: E402
from 地方の直前の買い目.repository import ExactaPayoutRepository, TrifectaPayoutRepository, WinPayoutRepository  # noqa: E402

DEFAULT_OUT = _TOOLS.parent / "reports" / "地方の直前の買い目" / "check.md"


def main(args: argparse.Namespace) -> None:
    rule = LateRule(args.likeness, args.payback, args.opponents, args.exacta_opponents)
    scored = LateWalkForward().run(LateTrainingTable(args.table).load())
    picks = [(str(rid), pick) for rid, race in scored.groupby(RACE_ID) for pick in rule.picks(race)]
    day_from, day_to = f"{scored[RACE_DATE].min():%Y%m%d}", f"{scored[RACE_DATE].max():%Y%m%d}"
    with db.open_db(args.db, default=db.LOCAL) as con:
        wins = WinPayoutRepository(con).load(day_from, day_to)
        settlement = LateSettlement(wins, ExactaPayoutRepository(con).load(day_from, day_to), TrifectaPayoutRepository(con).load(day_from, day_to))
    note = (f"買う馬らしさ {rule.likeness_line} 以上・戻りの見込み {rule.payback_line} 以上の馬。馬単は その馬 → 相手（相手は残りの、3着以内の確率の高い {rule.exacta_opponents} 頭）。3連単は その馬 → 相手 → 相手（相手は残りの人気上位 {rule.opponents} 頭）。"
            f"1点 100円。{scored[RACE_ID].nunique():,} レースのうち買ったのは {len({rid for rid, _ in picks}):,} レース。")
    table = LateSummary().table(settlement.settle(picks), "地方の直前の買い目: 時間の順を守った過去の成績", note)
    grade_note = (f"レースごとに、線にいちばん近い馬（買う馬らしさ ÷ {rule.likeness_line} と 戻りの見込み ÷ {rule.payback_line} の小さいほうがいちばん大きい馬）の"
                  f"単勝を 100円買ったときの成績。{LocalExpectationScale.legend()}。")
    grades = LateGradeTable(rule).table(scored, wins, "地方の期待度ごとの成績: 線にいちばん近い馬の単勝", grade_note)
    text = "\n\n".join(render.render(part, "markdown") for part in (table, grades))
    render.write(text, args.out, fmt="markdown")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--table", type=Path, default=DEFAULT_PATH, help=f"学習用の表（既定: {DEFAULT_PATH}）")
    parser.add_argument("--likeness", type=float, default=LIKENESS_LINE, help=f"買う馬らしさの線（既定: {LIKENESS_LINE}）")
    parser.add_argument("--payback", type=float, default=PAYBACK_LINE, help=f"戻りの見込みの線（既定: {PAYBACK_LINE}）")
    parser.add_argument("--opponents", type=int, default=OPPONENTS, help=f"3連単の相手の頭数（既定: {OPPONENTS}）")
    parser.add_argument("--exacta-opponents", type=int, default=EXACTA_OPPONENTS, help=f"馬単の相手の頭数（既定: {EXACTA_OPPONENTS}）")
    parser.add_argument("--db", type=Path, default=None, help="地方の元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"結果を書く先（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
