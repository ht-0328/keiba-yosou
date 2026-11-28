"""その日の結果の表（レースごと・合計）を作る。"""

from __future__ import annotations

from datetime import date
from typing import Any

from 共通.render import Table

from 今週の予想.high_payout_summary import LABEL as HIGH_PAYOUT_LABEL
from 今週の予想.public_rule import LABEL as PUBLIC_RULE_LABEL
from 今週の予想.ticket_rules import HIGH_PAYOUT_LABELS, HIGH_PAYOUT_TICKET_TYPES, POINT_YEN

from その日の結果.race_result import RaceResult, Settled

#: 合計の表の行（名前, RaceResult の精算の関数の名前）。
_KINDS: tuple[tuple[str, str], ...] = (("実際に買う買い目", "plan"), ("印の買い目（AI だけ）", "marks"), ("印の買い目（AI＋ロジック）", "logic"),
                                      (PUBLIC_RULE_LABEL, "public_rule"))
WAITING = "結果待ち"
#: 合計の表の、高配当の買い目の全部の券種を足した行の名前。
HIGH_PAYOUT_TOTAL = f"{HIGH_PAYOUT_LABEL}（合計）"


class DayTables:
    def build(self, day: date, results: list[tuple[dict[str, Any], RaceResult]]) -> list[Table]:
        """``results`` は（予想の JSON, そのレースの結果）の並び（rid の順）。"""
        return [self._races(day, results), self._totals(day, results)]

    def _races(self, day: date, results: list[tuple[dict[str, Any], RaceResult]]) -> Table:
        rows = []
        for forecast, result in results:
            header = forecast.get("header") or {}
            head = [f"{header.get('競馬場', '')} {header.get('R', '')}R", forecast.get("timing", ""), result.marks_line()]
            if not result.finished:
                rows.append([*head, WAITING, "", "", "", "", "", ""])
                continue
            skip = result.logic_skip()
            logic = f"見送り（{skip}）" if skip else result.logic().text()
            rows.append([*head, result.top3(), result.top_finish(), result.plan().text(), result.marks().text(), logic, result.high_payout().text(),
                         result.public_rule().text()])
        columns = ["レース", "時点", "印", "1〜3着（馬番と印）", "◎", "実際に買う買い目", "印の買い目（AI だけ）", "印の買い目（AI＋ロジック）",
                   HIGH_PAYOUT_LABEL, PUBLIC_RULE_LABEL]
        return Table(columns, rows, title=f"{day} の結果（レースごと。買った額 → 戻った額）")

    def _totals(self, day: date, results: list[tuple[dict[str, Any], RaceResult]]) -> Table:
        finished = [result for _, result in results if result.finished]
        rows = [self._total(name, [getattr(result, method)() for result in finished]) for name, method in _KINDS]
        rows += self._high_payout_totals(finished)
        top = [result.top_finish() for result in finished]
        note = (f"結果の届いたレース {len(finished)}／予想のあるレース {len(results)}。◎ は 1着 {top.count('1着')}・2着 {top.count('2着')}・"
                f"3着 {top.count('3着')}・着外 {top.count('着外')}。{self._dangers(finished)}。印の買い目は 1レース 5,000円を割合で配った額。"
                f"{HIGH_PAYOUT_LABEL}は 1点 {POINT_YEN}円で、券種ごとの行の「買ったレース」「当たったレース」はその券種を買った・当てたレースの数")
        return Table(["買い方", "買ったレース", "当たったレース", "投資", "払戻", "回収率", "収支"], rows, title=f"{day} の合計", note=note)

    def _high_payout_totals(self, finished: list[RaceResult]) -> list[list[Any]]:
        """高配当の買い目の行（券種ごとと合計）。券種の行は、今の対象の券種（``HIGH_PAYOUT_TICKET_TYPES``）と、その日に買った点のある券種だけ。"""
        by_type = {ticket_type: self._high_payout_settled(finished, ticket_type.label) for ticket_type in HIGH_PAYOUT_LABELS}
        shown = [ticket_type for ticket_type, settled in by_type.items() if ticket_type in HIGH_PAYOUT_TICKET_TYPES or _any_bought(settled)]
        rows = [self._total(f"{HIGH_PAYOUT_LABEL}（{ticket_type.label}）", by_type[ticket_type]) for ticket_type in shown]
        return [*rows, self._total(HIGH_PAYOUT_TOTAL, [result.high_payout() for result in finished])]

    @staticmethod
    def _high_payout_settled(finished: list[RaceResult], ticket_type: str) -> list[Settled]:
        """レースごとの、高配当の買い目の1つの券種の精算。"""
        return [result.high_payout_of(ticket_type) for result in finished]

    @staticmethod
    def _dangers(finished: list[RaceResult]) -> str:
        """消の数と、1着になった数（AI だけの予想と AI＋ロジック予想）。"""
        ai = [won for won in (result.danger_won() for result in finished) if won is not None]
        logic = [won for won in (result.logic_danger_won() for result in finished) if won is not None]
        return f"消は AI だけ {len(ai)}頭（1着 {sum(ai)}）・AI＋ロジック {len(logic)}頭（1着 {sum(logic)}）"

    @staticmethod
    def _total(name: str, settled: list[Settled]) -> list[Any]:
        bought = [one for one in settled if one.stake]
        stake, back = sum(one.stake for one in bought), sum(one.back for one in bought)
        rate = f"{back / stake:.1%}" if stake else "-"
        return [name, len(bought), sum(1 for one in bought if one.back > 0), f"{stake:,}円", f"{back:,}円", rate, f"{back - stake:+,}円"]


def _any_bought(settled: list[Settled]) -> bool:
    """どれかのレースで買ったか。"""
    return any(one.stake for one in settled)
