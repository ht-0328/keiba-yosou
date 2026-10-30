"""1レースの予想の結果を、人が読む文（印の付いた馬・買い目・◎ の理由と近走）にする。"""

from __future__ import annotations

from typing import Any

from yosou.review import names

from 今週の予想.mark_rule import NO_MARK, OUT_MARK, TOP_MARK
from 今週の予想.race_grades import RaceGrades
from 今週の予想.race_plan import RacePlan
from 今週の予想.ticket_pick import TicketPick
from 今週の予想.ticket_rules import PLACE_LABEL, POINT_YEN

#: 単勝・馬単用の財布で買う券種（単勝（期待値）と、◎の単勝の期待値が 1.00 以上のレースの ◎ の馬単）。
WIN_WALLET_TICKETS: tuple[str, ...] = ("単勝", "馬単")
#: 組の期待値の買い目を書く券種の順（実際に買うのは、今の決まりで採用したものだけが計画に入る）。
COMBO_LABELS: tuple[str, ...] = ("枠連", "馬連", "馬単", "ワイド", "3連複", "3連単")
#: 参考の買い目で、組を書き出す点数の上限（3連単のマルチは 60点を超えるので、期待値の高い順にここまで）。
REFERENCE_SHOWN = 10
#: 参考の買い目に出さない、比べるためだけの行（2モデル一致で絞った行）の目印。
REFERENCE_SKIP = "2モデル一致"


class RaceDescriber:
    """1レースの予想の結果（``RaceForecaster.forecast`` の辞書。保存した JSON と同じ形）を、印の付いた馬・危険な人気馬・
    買い目（実際に買うものと参考）・◎ の理由と近走だけに絞った Markdown にする。
    次のレースの予想（スキル）と、開催日ごとのまとめ（``DaySummary``）が同じ文を使う。

    ``plan`` はそのレースの買う計画（``RacePlan``）。あれば複勝の参加の種類と金額、単勝・馬単・組の期待値の買い目の金額を書く。
    無ければ（財布かオッズが無い）、複勝は期待値が線以上の馬だけを書く。
    """

    def describe(self, forecast: dict[str, Any], plan: RacePlan | None = None) -> str:
        return "\n".join(self.lines(forecast, plan))

    def lines(self, forecast: dict[str, Any], plan: RacePlan | None = None) -> list[str]:
        lines = [f"### {forecast['title']}",
                 f"時点: {forecast['timing']}（{forecast['timing_reason']}）。{RaceGrades.from_dict(forecast).text()}。"]
        for horse in forecast["horses"]:
            # 無印（－）の馬は出さない。前の版の予想（印の無い馬も「消」）は、危険な人気馬でない消を出さない
            if horse["mark"] == NO_MARK or (horse["mark"] == OUT_MARK and not horse.get("is_danger")):
                continue
            lines.append(self._horse_line(horse))
        lines += self._ticket_lines(forecast, plan)
        top = next((horse for horse in forecast["horses"] if horse["mark"] == TOP_MARK), None)
        if top is not None:
            lines.append(f"◎ の理由: {top['summary']}")
            # 近走の文（道具「近走の文」が付けた行。前の版の予想には無い）
            story = top.get("story") or {}
            if story.get("lines"):
                lines.append("◎ の近走（古い順）:")
                lines += story["lines"]
        return lines

    def _horse_line(self, horse: dict[str, Any]) -> str:
        popularity = int(horse["popularity"]) if isinstance(horse.get("popularity"), (int, float)) else "-"
        # 馬番は、枠順がまだ無い木曜（出走馬名表）の予想では無い
        horse_no = str(horse["horse_no"]) if horse.get("horse_no") is not None else "-"
        line = (f"{horse['mark']} {horse_no:>2} {horse['horse_name']}  {popularity}人気 {horse.get('win_odds') or '-'}倍"
                f"  3着内 {horse['probability'] * 100:.0f}%  単勝の期待値 {_number(horse.get('win_value'))}"
                f"  複勝の期待値 {_number(horse.get('place_value'))}")
        if horse.get("is_danger"):
            line += "  （危険な人気馬なので消）"
        return line

    def _place_lines(self, forecast: dict[str, Any], plan: RacePlan | None) -> list[str]:
        """複勝の行。計画があれば参加の種類・金額・理由、無ければ期待値が線以上の馬だけ。"""
        by_number = {horse["horse_no"]: horse for horse in forecast["horses"]}
        if plan is not None:
            if not plan.picks:
                return [f"- 複勝: なし（{plan.reason}）"]
            shown = "・".join(f"{pick.horse_no} {by_number.get(pick.horse_no, {}).get('horse_name', '')}"
                              f"（期待値 {_number(pick.value)}、{pick.yen:,}円）" for pick in plan.picks)
            return [f"- 複勝（{plan.kind}）: {shown}  合計 {plan.place_yen:,}円", f"  （{plan.reason}）"]
        place = []
        for ticket in forecast["tickets"]:
            if ticket["rule"] != PLACE_LABEL:
                continue
            horse = by_number.get(ticket["horses"][0], {})
            note = f"（期待値 {_number(horse.get('place_value'))}" + (f"、{ticket['dropped']}で外す）" if ticket["dropped"] else "）")
            place.append(f"{ticket['label']} {horse.get('horse_name', '')}{note}")
        return ["- 複勝: " + ("・".join(place) if place else "なし") + "（財布かオッズが無いので金額は出さない）"]

    def _ticket_lines(self, forecast: dict[str, Any], plan: RacePlan | None) -> list[str]:
        """買い目の行。実際に買う複勝・単勝・馬単・組の期待値の買い目（今の決まり）と、参考の券種（ワイド・馬連・3連複・3連単など）。"""
        lines = ["実際に買う買い目:", *self._place_lines(forecast, plan)]
        tickets = plan.tickets if plan is not None else ()
        win_picks = [pick for pick in tickets if pick.kind != names.MATCH_COMBO]
        combo_picks = [pick for pick in tickets if pick.kind == names.MATCH_COMBO]
        lines += self._bought_lines(WIN_WALLET_TICKETS, win_picks, "")
        if not win_picks:
            lines.append("- 単勝・馬単: なし（単勝（期待値）の馬がいない。馬単は ◎の単勝の期待値が 1.00 以上のレースだけ。くわしくは下の理由）")
        lines += self._bought_lines(COMBO_LABELS, combo_picks, "（組の期待値）")
        if not combo_picks:
            lines.append("- 組の期待値の買い目（枠連・馬連・馬単・ワイド・3連複・3連単）: なし（"
                         + ("当日の予想でないので買わない" if forecast.get("timing") != "当日" else "組の期待値が線以上の組が無いか、下の理由のとおり") + "）")
        if plan is not None and plan.ticket_reason:
            lines.append(f"  （{plan.ticket_reason}）")
        bought = {pick.ticket_type for pick in win_picks} | {f"{pick.ticket_type}（組の期待値）" for pick in combo_picks}
        lines.append(f"参考の買い目（回収率 100% 超えをまだ確かめられていない買い方。金額は1点 {POINT_YEN}円で数えた額）:")
        # 買い方は予想に入っている順（MarkTickets が組んだ順。前の版の予想は買い方の名前が違うことがあるので、名前の一覧では引かない）
        for rule in dict.fromkeys(ticket["rule"] for ticket in forecast["tickets"]):
            if rule == PLACE_LABEL or REFERENCE_SKIP in rule or rule in bought:
                continue
            lines.append(self._reference_line(rule, [ticket for ticket in forecast["tickets"] if ticket["rule"] == rule]))
        return lines

    def _bought_lines(self, labels: tuple[str, ...], picks: list[TicketPick], suffix: str) -> list[str]:
        """実際に買う券種ごとの行（組・期待値・オッズと、1点の額 × 点数）。"""
        lines = []
        for label in labels:
            chosen = sorted((pick for pick in picks if pick.ticket_type == label), key=lambda pick: -(pick.value or 0.0))
            if not chosen:
                continue
            shown = "・".join(f"{pick.label}（" + (f"期待値 {_number(pick.value)}・" if pick.value is not None and suffix else "")
                             + f"オッズ {_number(pick.odds, 1)}）" for pick in chosen[:REFERENCE_SHOWN])
            more = f" ほか {len(chosen) - REFERENCE_SHOWN}点" if len(chosen) > REFERENCE_SHOWN else ""
            total = sum(pick.yen for pick in chosen)
            lines.append(f"- {label}{suffix}: {shown}{more}  1点 {chosen[0].yen:,}円 × {len(chosen)}点 = {total:,}円")
        return lines

    def _reference_line(self, rule: str, tickets: list[dict[str, Any]]) -> str:
        """参考の買い方1つの行。買う組を期待値（無ければ並び）の順に最大 ``REFERENCE_SHOWN`` 点と、点数・金額の目安。トリガミで外す組は数だけ。"""
        kept = [ticket for ticket in tickets if not ticket["dropped"]]
        kept.sort(key=lambda ticket: -(ticket["value"] if ticket["value"] is not None else 0.0))
        yen = POINT_YEN * len(kept)
        shown = "・".join(ticket["label"] for ticket in kept[:REFERENCE_SHOWN])
        more = f" ほか {len(kept) - REFERENCE_SHOWN}点" if len(kept) > REFERENCE_SHOWN else ""
        dropped = f"（トリガミ・オッズ無しで外す {len(tickets) - len(kept)}点）" if len(kept) < len(tickets) else ""
        if not kept:
            return f"- {rule}: なし{dropped}"
        return f"- {rule}: {len(kept)}点 {yen:,}円  {shown}{more}{dropped}"


def _number(value: Any, digits: int = 2) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "-"
