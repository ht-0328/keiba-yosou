"""研究「的中実績の公開ルール」: 公開ルール（◎ の単勝。◎ の単勝の期待値が線以上・単勝オッズが上限以下のレースだけ）の成績を、
確定オッズの全期間と、発走10分前の単勝オッズで選んだ約1年で出す。

    uv run python research/的中実績の公開ルール/analysis/check.py                 # 線は本番（tools/今週の予想/public_rule.py）と同じ
    uv run python research/的中実績の公開ルール/analysis/check.py --minutes 8     # 締め切り前の断面を8分前にする

予測は研究「既存モデルの改善」の ``predictions/graded_race_day/odds_move-win.pkl``（今の本番の当日の予想と同じ作りの、学習に使っていない期間の予測）。
元DB は読むだけ（確定の単勝オッズ・単勝の払戻・時系列オッズの断面）。出るもの（Git 対象外）: ``reports/的中実績の公開ルール/check.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "tools"), str(_ROOT / "src"), str(_ROOT / "research")]

from 共通 import db, render  # noqa: E402
from 今週の予想.public_rule import ODDS_CAP, VALUE_LINE  # noqa: E402
from 的中実績の公開ルール.analysis.horse_table import HorseTable  # noqa: E402
from 的中実績の公開ルール.analysis.repository.pre_deadline_win_odds_repository import PreDeadlineWinOddsRepository  # noqa: E402
from 的中実績の公開ルール.analysis.rule_report import RuleReport  # noqa: E402
from 的中実績の公開ルール.analysis.top_picks import TopPicks  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.repository import PayoutRepository, RaceDayRange  # noqa: E402
from yosou.shared.repository.final_odds_repository import FinalOddsRepository  # noqa: E402

PREDICTIONS = _ROOT / "reports" / "既存モデルの改善" / "predictions" / "graded_race_day" / "odds_move-win.pkl"
OUT = _ROOT / "reports" / "的中実績の公開ルール"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=int, default=10, help="締め切り前の断面を、発走の何分前までのものにするか（既定 10）")
    parser.add_argument("--db", help="元DB の場所（省略すると既定の元DB）")
    args = parser.parse_args()
    predictions = pd.read_pickle(PREDICTIONS)
    days = pd.to_datetime(predictions["開催日"])
    first, last = days.min().date(), days.max().date()
    with db.open_db(args.db) as con:
        table = HorseTable(predictions, FinalOddsRepository(con, TicketType.WIN).read(RaceDayRange(first, last)),
                           PayoutRepository(con, TicketType.WIN).read(RaceDayRange(first, last)),
                           PreDeadlineWinOddsRepository(con, first, last, args.minutes).read())
    picks = TopPicks()
    report = RuleReport(picks.of(table.final()), picks.of(table.snapshot()), VALUE_LINE, ODDS_CAP, f"{args.minutes}分前のオッズ")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ("check.md" if args.minutes == 10 else f"check_{args.minutes}分前.md")
    render.write(render.render(report.tables(), "markdown"), out, fmt="markdown")
    print(render.render(report.tables(), "markdown"))
    print(f"書いた: {out}（予測 {first:%Y-%m-%d}〜{last:%Y-%m-%d}）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
