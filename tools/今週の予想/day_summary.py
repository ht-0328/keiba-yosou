"""1開催日の保存してある予想と計画から、人が読むまとめ（一覧・買うレース・レースごとの印と買い目）の Markdown を作る。"""

from __future__ import annotations

from datetime import date
from itertools import groupby
from typing import Any

from 共通.render import Table, to_markdown

from 今週の予想.day_planner import GRADED_CLASSES
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.mark_rule import RANK_MARKS, TOP_MARK
from 今週の予想.plan_store import PlanStore
from 今週の予想.plan_table import PlanTable
from 今週の予想.race_describer import RaceDescriber
from 今週の予想.race_grades import RaceGrades
from 今週の予想.race_plan import RacePlan

#: 一覧の列。
OVERVIEW_COLUMNS: list[str] = ["場R", "レース名", "条件", "発走", "時点", "◎ランク（的中率）", "配当率", "◎", "○", "▲", "消", "買う"]
#: 曜日の字（``date.weekday`` の順）。
WEEKDAYS = "月火水木金土日"
#: 見出しに書く時点の順。
TIMING_ORDER: tuple[str, ...] = ("当日", "前日", "木曜")
#: 計画（plan.json）が無い日の文。
NO_PLAN_TEXT = "計画はまだ無い（木曜の予想はオッズが無いので決めない。前日・当日の予想なら forecast.py が全レースの予想のあとに決める）"
#: 短い版で、レースの文が1つも無いときの文。
NOTHING_FEATURED_TEXT = "（平地の重賞と実際に買うレースはありません。全レースの文は同じフォルダの まとめ.md にあります）"


class DaySummary:
    """1開催日のまとめの Markdown。保存してある予想（``<置き場所>/<開催日>/<rid>.json``）と計画（``plan.json``）だけから作り、
    DB は開かない（forecast.py が予想している間でも出せる）。

    中身は、見出し（予想した数と時点の内訳・買う合計）→ 一覧（1行1レース）→ 買うレース（計画の表）→ 競馬場ごとにレースの文
    （``RaceDescriber``。印・買い目・◎ の理由と近走）。``brief=True`` は、レースの文を平地の重賞と実際に買うレースだけにする
    （チャットに貼れる長さ。次のレースの予想のスキルと同じ文）。
    """

    def __init__(self, forecasts: ForecastStore, plans: PlanStore | None = None, describer: RaceDescriber | None = None) -> None:
        self._forecasts = forecasts
        self._plans = plans or PlanStore(forecasts)
        self._describer = describer or RaceDescriber()

    def markdown(self, day: date, *, brief: bool = False) -> str:
        forecasts = self._forecasts.load_day(day)
        title = f"# {day.isoformat()}（{WEEKDAYS[day.weekday()]}） の予想のまとめ"
        if not forecasts:
            return f"{title}\n\n（予想がありません）\n"
        payload = self._plans.load(day)
        plans = {race["rid"]: RacePlan.from_dict(race) for race in (payload or {}).get("races", [])}
        lines = [title, "", *self._head(forecasts, payload, plans), "",
                 "## 一覧", "", to_markdown(self._overview(forecasts, plans)), "",
                 "## 買うレース", "", *self._plan_lines(day, payload, plans), "",
                 *self._race_sections(forecasts, plans, brief)]
        return "\n".join(lines).rstrip("\n") + "\n"

    def _head(self, forecasts: list[dict[str, Any]], payload: dict[str, Any] | None, plans: dict[str, RacePlan]) -> list[str]:
        """見出しの箇条書き（予想した数と時点の内訳・買う合計・全頭の根拠の場所）。"""
        counts = {timing: sum(1 for forecast in forecasts if forecast["timing"] == timing) for timing in TIMING_ORDER}
        counts.update({forecast["timing"]: counts.get(forecast["timing"], 0) + 1 for forecast in forecasts if forecast["timing"] not in TIMING_ORDER})
        breakdown = "・".join(f"{timing} {count}" for timing, count in counts.items() if count)
        made_at = max((forecast.get("made_at") or "" for forecast in forecasts), default="")
        lines = [f"- 予想 {len(forecasts)} レース（{breakdown}）。作った時刻 {made_at[:16].replace('T', ' ')}（いちばん新しいもの）"]
        if payload is None:
            lines.append(f"- {NO_PLAN_TEXT}")
        else:
            bought = [plan for plan in plans.values() if plan.buys]
            total = sum(plan.stake_yen for plan in bought)
            lines.append(f"- 実際に買う: {len(bought)} レース・合計 {total:,}円（計画は同じフォルダの plan.json）" if bought
                         else "- 実際に買う: なし（計画で買うレースが無い）")
        lines.append("- 全頭の予想根拠（馬ごとの確率・総合・良い点と悪い点・近走）は同じフォルダの <rid>.md。画面は検索画面の「今週の予想」タブ")
        return lines

    def _overview(self, forecasts: list[dict[str, Any]], plans: dict[str, RacePlan]) -> Table:
        """一覧の表（1行1レース。rid の順 = 競馬場のコード・レース番号の順）。"""
        return Table(OVERVIEW_COLUMNS, [self._overview_row(forecast, plans.get(forecast["rid"])) for forecast in forecasts])

    def _overview_row(self, forecast: dict[str, Any], plan: RacePlan | None) -> list[Any]:
        header = forecast.get("header") or {}
        first_by_mark: dict[str, dict[str, Any]] = {}
        for horse in forecast["horses"]:
            first_by_mark.setdefault(horse["mark"], horse)
        danger = next((horse for horse in forecast["horses"] if horse.get("is_danger")), None)
        grades = RaceGrades.from_dict(forecast)
        name, klass = header.get("レース名") or "", header.get("クラス") or ""
        return [f"{header.get('競馬場', '')} {header.get('R', '')}R",
                f"{name}（{klass}）" if name else klass,
                f"{header.get('コース', '')} {header.get('距離', '')}m {header.get('頭数', '')}頭",
                header.get("発走", ""),
                forecast["timing"],
                "" if grades.rank is None else f"{grades.rank}（{_percent(grades.hit_rate)}）",
                "" if grades.payout_grade is None else f"{grades.payout_grade}（{_percent(grades.payout_rate)}）",
                _top_text(first_by_mark.get(TOP_MARK)),
                _horse_text(first_by_mark.get(RANK_MARKS[0])),
                _horse_text(first_by_mark.get(RANK_MARKS[1])),
                _horse_text(danger),
                _buy_text(plan)]

    def _plan_lines(self, day: date, payload: dict[str, Any] | None, plans: dict[str, RacePlan]) -> list[str]:
        """買うレースの表（計画の表 ``PlanTable`` と同じ。見出しはこちらで付けるので表の題は出さない）。"""
        if payload is None:
            return [NO_PLAN_TEXT]
        table = PlanTable().table(day, list(plans.values()), payload["wallet"])
        table.title = ""
        return [to_markdown(table)]

    def _race_sections(self, forecasts: list[dict[str, Any]], plans: dict[str, RacePlan], brief: bool) -> list[str]:
        """競馬場ごとの見出しと、レースごとの文。短い版は平地の重賞と実際に買うレースだけ。"""
        lines: list[str] = []
        for venue, group in groupby(forecasts, key=lambda forecast: (forecast.get("header") or {}).get("競馬場", "")):
            shown = [forecast for forecast in group if not brief or self._featured(forecast, plans.get(forecast["rid"]))]
            if not shown:
                continue
            lines += [f"## {venue}", ""]
            for forecast in shown:
                lines += [*self._describer.lines(forecast, plans.get(forecast["rid"])), ""]
        if brief and not lines:
            lines.append(NOTHING_FEATURED_TEXT)
        return lines

    @staticmethod
    def _featured(forecast: dict[str, Any], plan: RacePlan | None) -> bool:
        """短い版に文を載せるレースか（平地の重賞か、実際に買うレース）。"""
        if plan is not None and (plan.graded or plan.buys):
            return True
        return str((forecast.get("header") or {}).get("クラス", "")) in GRADED_CLASSES


def _percent(rate: float | None) -> str:
    return "なし" if rate is None else f"{rate:.0%}"


def _horse_text(horse: dict[str, Any] | None) -> str:
    """馬番と馬名（枠順がまだ無い木曜の予想は馬名だけ）。"""
    if horse is None:
        return ""
    return horse["horse_name"] if horse.get("horse_no") is None else f"{horse['horse_no']} {horse['horse_name']}"


def _top_text(horse: dict[str, Any] | None) -> str:
    """◎ の馬（人気と単勝オッズがあれば添える。木曜の予想には無い）。"""
    if horse is None:
        return ""
    text = _horse_text(horse)
    if isinstance(horse.get("popularity"), (int, float)) and horse.get("win_odds"):
        text += f"（{int(horse['popularity'])}人気 {horse['win_odds']}倍）"
    return text


def _buy_text(plan: RacePlan | None) -> str:
    """一覧の「買う」の列。計画が無ければ空、買わなければ「買わない」、買うなら券種と金額。"""
    if plan is None:
        return ""
    parts = []
    if plan.place_yen:
        parts.append(f"複勝（{plan.kind}）{plan.place_yen:,}円")
    if plan.ticket_yen:
        kinds = "・".join(dict.fromkeys(ticket.ticket_type for ticket in plan.tickets))
        parts.append(f"{kinds} {plan.ticket_yen:,}円")
    return "、".join(parts) or "買わない"
