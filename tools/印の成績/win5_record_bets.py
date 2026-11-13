"""実際に予想した結果の記録（``predict`` が自動で書いたもの）の買い目を精算する。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from yosou.form_aptitude_win5_tickets.formation import DayDecision, Formation
from yosou.form_aptitude_win5_tickets.repository import Win5ForecastRecordRepository
from yosou.form_aptitude_win5_tickets.repository.win5_forecast_record_repository import FOLDER_NAME
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY, Win5Outcome, Win5Settlement

from 印の成績.win5_bet_columns import BUDGET, CARRY_DAY, EXPECTED_VALUE, FAVORITE_PRODUCT, KIND, LARGE_DAY

#: 実際の予想の買い方の名前と種類。
RECORDED = "実際の予想（記録。締め切り前のオッズ）"
RECORDED_KIND = "実際の予想"


class Win5RecordBets:
    """設計書「近走と適性からWIN5の買い目を決める」15 の 7・16 の 7.。``predict`` が ``<root>/記録/<開催日>.json`` に残した実際の予想のうち、
    判断が買う日（「買う（多く）」「買う（少なく）」。段階の予算より前の記録の「買う」も）で、元DB に結果（成績の版）のある日の買い目
    （段階の予算なら、その段階で買った買い目と代金）を ``Win5Settlement`` で精算し、確定オッズで確かめた成績と同じ表に並べる行にする。"""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._repository = Win5ForecastRecordRepository(self._root)

    def rows(self, outcomes: dict[str, Win5Outcome]) -> tuple[list[dict[str, object]], str]:
        """（買った日の精算の行, 記録の数を書いた文）。"""
        days = sorted(path.stem for path in (self._root / FOLDER_NAME).glob("*.json"))
        rows, bought = [], 0
        for day in days:
            record = self._repository.load(date.fromisoformat(day))
            if not DayDecision.buys_text(str(record.get("判断", DayDecision.SKIP.label))):
                continue
            bought += 1
            if day in outcomes:
                rows.append(self._row(record, outcomes[day]))
        note = f"実際の予想の記録 {len(days)}日（買う {bought}日、そのうち結果の出た日 {len(rows)}日）"
        return rows, note

    def _row(self, record: dict[str, object], outcome: Win5Outcome) -> dict[str, object]:
        formation = Formation(tuple(tuple(int(number) for number in picks) for picks in record["買い目"]))
        settled = Win5Settlement().settle(formation, outcome)
        favorite = record.get("本命の確率の積")
        return {
            STRATEGY: RECORDED, KIND: RECORDED_KIND, BUDGET: int(record["予算"]), RACE_DATE: outcome.race_date, STAKE: settled.stake,
            PAYOUT: settled.payout, HIT: settled.hit, CARRY_DAY: int(record.get("キャリーオーバー", 0)) > 0,
            EXPECTED_VALUE: float(record.get("判断用の期待値", record["日の期待値"])),
            LARGE_DAY: record.get("判断") == DayDecision.BUY_LARGE.label,
            FAVORITE_PRODUCT: float("nan") if favorite is None else float(favorite),
        }
