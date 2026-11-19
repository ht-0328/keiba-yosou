"""通知のときのオッズで作った推奨買目の期待の儲けが、目安として使えるかを確かめる（研究「地方の期待度」の docs/03）。

    uv run python research/地方の期待度/notified.py --db <元DB の写し>     # 開催日のレースの時間は、元DB でなく写しを渡す
    uv run python research/地方の期待度/notified.py --from 2026-11-09

発走前の通知が保存した予想（reports/発走前の通知/地方/<開催日>/<rid>.json）と、そのとき元DB に入った途中のオッズで推奨買目を作り直し、
確定の払戻を当てて、期待の儲けの等級ごと・点数の高低ごとの成績を書く。出るもの（Git 対象外）: reports/地方の期待度/通知のときの期待の儲け.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

import pandas as pd  # noqa: E402

from 共通 import cli, db, render  # noqa: E402
from 地方の期待度.analysis.notified_bets import NotifiedBets  # noqa: E402
from 地方の期待度.analysis.notified_grade_table import NotifiedGradeTable  # noqa: E402
from 地方の期待度.analysis.notified_payout_repository import TICKETS, NotifiedPayoutRepository  # noqa: E402
from 地方の期待度.analysis.late_snapshot_repository import LateSnapshotRepository  # noqa: E402
from 地方の推奨買目.coefficient_store import CoefficientStore  # noqa: E402
from 地方の推奨買目.recommender import Recommender  # noqa: E402
from 発走前の通知.saved_upset_probabilities import SavedUpsetProbabilities  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の期待度" / "通知のときの期待の儲け.md"
DEFAULT_SAVED = _REPO_ROOT / "reports" / "発走前の通知" / "地方"
#: 通知が今の推奨買目（8券種）を出し始めた日。
DEFAULT_FROM = "2026-11-09"


def main(args: argparse.Namespace) -> None:
    day_from = args.day_from.replace("-", "")
    with db.open_db(args.db, default=db.LOCAL) as con:
        skip = LateSnapshotRepository(con).load(day_from)
        bets = NotifiedBets(Recommender(con, CoefficientStore().load(), upsets=SavedUpsetProbabilities()), args.saved, skip).build(args.day_from)
        repository = NotifiedPayoutRepository(con)
        payouts = pd.concat([repository.load(ticket, day_from, "99991231").assign(ticket=ticket) for ticket in TICKETS], ignore_index=True)
    settled = bets[bets["race_id"].isin(set(payouts["race_id"]))]
    priced = settled.merge(payouts, on=["race_id", "ticket", "numbers"], how="left").fillna({"payout": 0})
    note = (f"{args.day_from} 以降に通知が保存した当日の時点の予想と、通知のときのオッズで作り直した推奨買目（1点 100円）。払戻は確定の値。"
            f"結果のあるレースだけ。締め切り後に取り込んだ断面のある {len(skip)} レースは数えない。")
    text = render.render(NotifiedGradeTable().table(priced, "通知のときの推奨買目: 期待の儲けの高低と成績", note), "markdown")
    render.write(text, args.out, fmt="markdown")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="地方の元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB。写しを渡せる）")
    parser.add_argument("--from", dest="day_from", default=DEFAULT_FROM, help=f"対象の最初の開催日 YYYY-MM-DD（既定: {DEFAULT_FROM}）")
    parser.add_argument("--saved", type=Path, default=DEFAULT_SAVED, help=f"通知の保存先（既定: {DEFAULT_SAVED}）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"結果を書く先（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
