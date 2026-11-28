"""研究「的中実績の公開ルール」（docs/02）: 今の公開ルール（全レースと勝負の2段）の成績を、確率を直すモデルを年ごとに学び直して数える。

    uv run python research/的中実績の公開ルール/analysis/walk_forward.py                # 勝負の線は本番（tools/今週の予想/public_rule_picker.py）と同じ
    uv run python research/的中実績の公開ルール/analysis/walk_forward.py --minutes 8    # 締め切り前の断面を8分前にする

年ごとに、その年より前の年（2020年から）の確定オッズの表だけで確率を直すモデル（``yosou.shared.win_correction``。本番と同じ設定）を学び、
その年の確定オッズの表と、締め切り前の断面の表（時系列オッズのある約1年）の確率を直す。◎・相手の決め方は本番と同じ（``PublicRulePicker.decide``）。
学習の表は道具「公開ルール」と同じ部品（``TrainingTable``・``TrainingInputReader``）で作る。元DB は読むだけで、事実表を作るので数分かかる。
出るもの（Git 対象外）: ``reports/的中実績の公開ルール/walk_forward.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "tools"), str(_ROOT / "src"), str(_ROOT / "research")]

from 共通 import db, render  # noqa: E402
from 今週の予想.public_rule_picker import SHOBU_LINE  # noqa: E402
from 印の成績.prediction_file import PredictionFile  # noqa: E402
from 公開ルール.folders import DEFAULT_TOP3, DEFAULT_WIN  # noqa: E402
from 公開ルール.repository.training_input_reader import TrainingInputReader  # noqa: E402
from 公開ルール.training_table import TrainingTable  # noqa: E402
from 的中実績の公開ルール.analysis.public_bets import PublicBets  # noqa: E402
from 的中実績の公開ルール.analysis.repository.pre_deadline_board_repository import BOARDS, PreDeadlineBoardRepository  # noqa: E402
from 的中実績の公開ルール.analysis.snapshot_table import SnapshotTable  # noqa: E402
from 的中実績の公開ルール.analysis.tier_report import TierReport  # noqa: E402
from 的中実績の公開ルール.analysis.walk_forward_model import WalkForwardModel  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.repository import PayoutRepository, RaceDayRange  # noqa: E402

OUT = _ROOT / "reports" / "的中実績の公開ルール"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=int, default=10, help="締め切り前の断面を、発走の何分前までのものにするか（既定 10）")
    parser.add_argument("--db", help="元DB の場所（開催中は写しを渡す）")
    args = parser.parse_args()
    win, top3 = PredictionFile(DEFAULT_WIN).load(), PredictionFile(DEFAULT_TOP3).load()
    tested = win[win["period"] == "テスト"]["race_date"].astype(str).str[:10]
    days = RaceDayRange(date.fromisoformat(tested.min()), date.fromisoformat(tested.max()))
    with db.open_db(args.db) as con:
        inputs = TrainingInputReader().read(con, days)
        exacta = PayoutRepository(con, TicketType.EXACTA).read(days)
        repository = PreDeadlineBoardRepository(con, days.first_day, days.last_day, args.minutes)
        boards = {name: repository.read(name) for name in BOARDS}
    final = TrainingTable(win, top3, inputs.win_odds, inputs.place_odds, inputs.quinella_odds, inputs.win_payouts, inputs.facts).build()
    snapshot = SnapshotTable(final, boards).build()
    final_corrected, snapshot_corrected = WalkForwardModel(final).predict([final, snapshot])
    report = TierReport(PublicBets(final_corrected, inputs.win_payouts, exacta).races(), PublicBets(snapshot_corrected, inputs.win_payouts, exacta).races(),
                        SHOBU_LINE, f"{args.minutes}分前のオッズ")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ("walk_forward.md" if args.minutes == 10 else f"walk_forward_{args.minutes}分前.md")
    text = render.render(report.tables(), "markdown")
    render.write(text, out, fmt="markdown")
    print(text)
    print(f"書いた: {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
