"""1レースの高配当の買い目を、券種ごとにまとめて文にする。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import Any

from 今週の予想.forecast_columns import HIGH_PAYOUT
from 今週の予想.ticket_rules import HIGH_PAYOUT_LABELS, POINT_YEN

#: 高配当の買い目を出す時点（予想の JSON の timing）。
_RACE_DAY = "当日"
#: 見出しのことば。
LABEL = "高配当の買い目"
#: 発走前の通知で、1行に書く組の数の上限（超えたら次の行に続ける。Discord の投稿を行の切れ目で分けても、組の途中で切れないように）。
NOTICE_ROW_POINTS = 10
#: 発走前の通知の、続きの行の頭の字下げ。
_CONTINUED = "  "


@dataclass(frozen=True)
class HighPayoutSummary:
    """予想の結果（保存した JSON と同じ形の辞書）の高配当の買い目（買い方の名前が ``HIGH_PAYOUT_LABELS`` の点。外した点は除く）を、
    券種ごとにまとめたもの。1レースの文（``RaceDescriber``）・発走前の通知（``RaceMessage``）・その日の結果（``RaceResult``）が同じものを使う。

    ``tickets`` は 券種の名前 → 買う点の並び（予想の JSON の買い目1点の辞書）。買う点の無い券種は入らない。
    ``conditions`` は買い目の決まり（``HighPayoutPicker.conditions``。期待値の線 ``value_line``・上限の点数 ``max_points``・
    券種の名前 → 高配当の線 ``high_lines``・学習済みモデルを読めたか ``ready``）。前の版の予想には無いので空。
    金額は1点 ``POINT_YEN`` 円で数える（財布と買う計画には入れない）。

    例: ワイド 3-9（24.5倍）と 3-12（31.0倍）が買う点なら、``points`` は 2、``yen`` は 200、通知の行は
    ``- ワイド（10倍以上）2点: 3-9（24.5倍）・3-12（31.0倍）``。
    """

    tickets: dict[str, list[dict[str, Any]]]
    conditions: dict[str, Any]
    race_day: bool

    @classmethod
    def of(cls, forecast: dict[str, Any]) -> HighPayoutSummary:
        kept = [ticket for ticket in forecast.get("tickets") or [] if not ticket.get("dropped")]
        by_type = {ticket_type.label: _of_rule(kept, rule) for ticket_type, rule in HIGH_PAYOUT_LABELS.items()}
        return cls({label: points for label, points in by_type.items() if points}, dict(forecast.get(HIGH_PAYOUT) or {}),
                   forecast.get("timing") == _RACE_DAY)

    @property
    def points(self) -> int:
        """買う点数（全部の券種）。"""
        return sum(len(points) for points in self.tickets.values())

    @property
    def yen(self) -> int:
        """買う金額（1点 ``POINT_YEN`` 円）。"""
        return POINT_YEN * self.points

    def stakes(self) -> list[tuple[str, str, int]]:
        """精算に使う、（券種の名前, 組番, 金額）の並び。"""
        return list(chain.from_iterable(self.stakes_of(label) for label in self.tickets))

    def stakes_of(self, label: str) -> list[tuple[str, str, int]]:
        """1つの券種の、（券種の名前, 組番, 金額）の並び。買う点の無い券種は空。"""
        return [(label, str(ticket["combo"]), POINT_YEN) for ticket in self.tickets.get(label, [])]

    def condition_text(self) -> str:
        """買い目の決まりの短い文。例 ``高配当の線以上・期待値 1.05 以上``（上限の点数があれば ``・1券種 10点まで``）。"""
        line = self.conditions.get("value_line")
        value = f"・期待値 {line:.2f} 以上" if isinstance(line, (int, float)) else ""
        cap = f"・1券種 {self.conditions['max_points']}点まで" if self.conditions.get("max_points") else ""
        return f"高配当の線以上{value}{cap}"

    def heading(self) -> str:
        """見出し。例 ``高配当の買い目（高配当の線以上・期待値 1.05 以上。1点 100円・合計 1,200円）``。"""
        return f"{LABEL}（{self.condition_text()}。1点 {POINT_YEN:,}円・合計 {self.yen:,}円）"

    def none_reason(self) -> str:
        """買う点が無い理由。"""
        if not self.race_day:
            return "当日の予想で出す"
        if not self.conditions:
            return "この予想には入っていない（前の版の予想）"
        if not self.conditions.get("ready"):
            return "高配当の予想の学習済みモデルが無い"
        return f"{self.condition_text()}の組が無い"

    def detail_lines(self) -> list[str]:
        """1レースの文の行（券種ごとに1行。期待値の高い順に全部の組・期待値・オッズと、1点の額 × 点数 = 金額。先頭の「- 」は付けない）。"""
        return [self._detail_line(label, points) for label, points in self.tickets.items()]

    def notice_lines(self) -> list[str]:
        """発走前の通知の行（そのまま投稿できる形。券種ごとに「- 」で始まる1行で、馬番の順に全部の組とオッズ。
        1行に ``NOTICE_ROW_POINTS`` 点までで、超えた分は字下げした次の行に続ける）。"""
        return list(chain.from_iterable(self._notice_rows(label, points) for label, points in self.tickets.items()))

    def _detail_line(self, label: str, points: list[dict[str, Any]]) -> str:
        ordered = sorted(points, key=lambda ticket: -(ticket.get("value") or 0.0))
        shown = "・".join(f"{ticket['label']}（期待値 {_number(ticket.get('value'), 2)}・オッズ {_number(ticket.get('odds'), 1)}）" for ticket in ordered)
        name = "・".join(part for part in ("高配当", self._high_line(label)) if part)
        return f"{label}（{name}）: {shown}  1点 {POINT_YEN:,}円 × {len(points)}点 = {POINT_YEN * len(points):,}円"

    def _notice_rows(self, label: str, points: list[dict[str, Any]]) -> list[str]:
        ordered = sorted(points, key=lambda ticket: str(ticket["combo"]))
        shown = [f"{ticket['label']}（{_number(ticket.get('odds'), 1)}倍）" for ticket in ordered]
        rows = ["・".join(shown[start:start + NOTICE_ROW_POINTS]) for start in range(0, len(shown), NOTICE_ROW_POINTS)]
        line = self._high_line(label)
        head = f"- {label}（{line}）" if line else f"- {label} "
        return [f"{head}{len(points)}点: {rows[0]}", *(f"{_CONTINUED}{row}" for row in rows[1:])]

    def _high_line(self, label: str) -> str:
        """券種の高配当の線。例 ``10倍以上``。決まりに無ければ（前の版の予想）空。"""
        line = (self.conditions.get("high_lines") or {}).get(label)
        return f"{line:g}倍以上" if isinstance(line, (int, float)) else ""


def _of_rule(tickets: list[dict[str, Any]], rule: str) -> list[dict[str, Any]]:
    """買い方の名前が ``rule`` の点。"""
    return [ticket for ticket in tickets if ticket.get("rule") == rule]


def _number(value: Any, digits: int) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "-"
