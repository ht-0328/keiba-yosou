"""実際に予想した結果の記録（``predict`` が自動で書いたもの）の買い目を精算する。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from yosou.form_aptitude_win5_tickets.formation import DayDecision, Formation
from yosou.form_aptitude_win5_tickets.repository import Win5ForecastRecordRepository
from yosou.form_aptitude_win5_tickets.repository.win5_forecast_record_repository import FOLDER_NAME
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY, Win5Outcome, Win5Settlement

from 印の成績.win5_day_bets import BUDGET, CARRY_DAY, EXPECTED_VALUE, KIND

#: 実際の予想の買い方の名前と種類。
RECORDED = "実際の予想（記録。締め切り前のオッズ）"
RECORDED_KIND = "実際の予想"


class Win5RecordBets:
    """設計書「近走と適性からWIN5の買い目を決める」15 の 7・16 の 7.。``predict`` が ``<root>/記録/<開催日>.json`` に残した実際の予想のうち、
    判断が「買う」で、元DB に結果（成績の版）のある日の買い目を ``Win5Settlement`` で精算し、確定オッズで確かめた成績と同じ表に並べる行にする。"""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._repository = Win5ForecastRecordRepository(self._root)

    def rows(self, outcomes: dict[str, Win5Outcome]) -> tuple[list[dict[str, object]], str]:
        """（買った日の精算の行, 記録の数を書いた文）。"""
        days = sorted(path.stem for path in (self._root / FOLDER_NAME).glob("*.json"))
        rows, bought = [], 0
        for day in days:
            record = self._repository.load(date.fromisoformat(day))
            if record.get("判断") != DayDecision.BUY.label:
                continue
            bought += 1
            if day in outcomes:
                rows.append(self._row(record, outcomes[day]))
        note = f"実際の予想の記録 {len(days)}日（買う {bought}日、そのうち結果の出た日 {len(rows)}日）"
        return rows, note

    def _row(self, record: dict[str, object], outcome: Win5Outcome) -> dict[str, object]:
        formation = Formation(tuple(tuple(int(number) for number in picks) for picks in record["買い目"]))
        settled = Win5Settlement().settle(formation, outcome)
        return {
            STRATEGY: RECORDED, KIND: RECORDED_KIND, BUDGET: int(record["予算"]), RACE_DATE: outcome.race_date, STAKE: settled.stake,
            PAYOUT: settled.payout, HIT: settled.hit, CARRY_DAY: int(record.get("キャリーオーバー", 0)) > 0,
            EXPECTED_VALUE: float(record["日の期待値"]),
        }
