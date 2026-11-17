"""地方の直前の買い目: 発走前の通知が実際に出した買い目の成績（実際の通知の時刻のオッズで決めた買い目を、確定の払戻で数える）。

    uv run python tools/地方の直前の買い目/results.py                                  # 通知が書いた全部の日
    uv run python tools/地方の直前の買い目/results.py --from 2026-11-18 --to 2026-11-30

買い目は発走前の通知が reports/発走前の通知/地方/<開催日>/<rid>.直前.json に書いたもの（人が記録するものは無い）。
払戻は元DB の払戻の表。結果のまだ無いレースは数えない。結果は標準出力と reports/地方の直前の買い目/results.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli, db, render  # noqa: E402

from 地方の直前の買い目.late_settlement import LateSettlement  # noqa: E402
from 地方の直前の買い目.late_summary import LateSummary  # noqa: E402
from 地方の直前の買い目.repository import TrifectaPayoutRepository, WinPayoutRepository  # noqa: E402
from 地方の直前の買い目.saved_late_bets import DEFAULT_FOLDER, SavedLateBets  # noqa: E402

DEFAULT_OUT = _TOOLS.parent / "reports" / "地方の直前の買い目" / "results.md"


def main(args: argparse.Namespace) -> None:
    saved = SavedLateBets(args.folder).read(args.date_from, args.date_to)
    if not saved:
        raise LookupError(f"直前の買い目のファイルがありません（{args.folder} の {args.date_from}〜{args.date_to}）")
    picks = [(rid, pick) for rid, bets in saved for pick in bets.picks]
    days = sorted({rid[:8] for rid, _ in saved})
    with db.open_db(args.db, default=db.LOCAL) as con:
        settlement = LateSettlement(WinPayoutRepository(con).load(days[0], days[-1]), TrifectaPayoutRepository(con).load(days[0], days[-1]))
    settled = settlement.settle(picks)
    unavailable = sum(1 for _, bets in saved if bets.empty and "いない" not in bets.reason)
    note = (f"通知が買い目を決めた {len(saved):,} レースのうち、買う馬がいたのは {len({rid for rid, _ in picks}):,} レース（{len(picks):,} 頭）、"
            f"材料がそろわず出せなかったのは {unavailable:,} レース。結果のあるのは {len(settled):,} 頭。1点 100円。")
    table = LateSummary().table(settled, f"地方の直前の買い目: 実際の通知の成績（{days[0]}〜{days[-1]}）", note)
    text = render.render(table, "markdown")
    render.write(text, args.out, fmt="markdown")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--from", dest="date_from", default="0000-00-00", help="最初の開催日 YYYY-MM-DD（既定: 最初から）")
    parser.add_argument("--to", dest="date_to", default="9999-99-99", help="最後の開催日 YYYY-MM-DD（既定: 最後まで）")
    parser.add_argument("--folder", type=Path, default=DEFAULT_FOLDER, help=f"通知が買い目を書いたフォルダ（既定: {DEFAULT_FOLDER}）")
    parser.add_argument("--db", type=Path, default=None, help="地方の元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"結果を書く先（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
