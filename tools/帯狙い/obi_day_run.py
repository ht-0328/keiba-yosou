"""1日の帯狙い: レースを選び、荒れる前提の予想で予想し、1万円の買い目を組む。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import duckdb

from 共通 import card

from yosou.shared.betting import TicketType
from yosou.upset_premise.betting import TicketPlan

from 今週の予想 import forecast_columns as columns
from 今週の予想.race_forecaster import RaceForecaster
from 帯狙い.announced_combo_odds import AnnouncedComboOdds
from 帯狙い.forecast_horses import ForecastHorses
from 帯狙い.obi_day_picker import ObiDayPicker, RaceChance

#: 買い目が参考であることの注記（研究「百万馬券を当てる」の docs/04 の 3 で、どの買い方も採用の基準に届かなかったため）。
REFERENCE_NOTE = "買い目は参考（過去の確かめで採用の基準に届かなかったので、財布にも買い目の記録にも書かない）。"
#: 結果に残す、荒れそうなレースの上位の数。
RANKING_COUNT = 5
#: 出馬表の一覧の rid の列。
_RID = card.CARD_LIST_HEADERS.index("rid")


class ObiDayRun:
    """1日の帯狙いを進める（ほかを順に呼ぶだけ）。

    1. その日のレースを、3連単の超荒れの確率の高い順に並べる（``ObiDayPicker``）。先頭のレースを選ぶ。
    2. 選んだレースを、荒れる前提のモデルの置き場所を渡した ``RaceForecaster`` で予想する（印・危険な人気馬の判定も今週の予想と同じ）。
    3. 3着以内と1着の確率と、締め切り前（なければ確定）の組ごとのオッズで、``plan`` の買い目を組む。
       オッズがまだ無ければ（木曜・前日でオッズの無いレース）、買い目は組まず、当日に組み直すことを書く。
    結果は JSON にできる辞書。
    """

    def __init__(self, picker: ObiDayPicker, forecaster: RaceForecaster, plan: TicketPlan) -> None:
        self._picker = picker
        self._forecaster = forecaster
        self._plan = plan

    def run(self, con: duckdb.DuckDBPyConnection, day: date) -> dict[str, Any]:
        listed = card.list_cards(con, date_from=day.isoformat(), date_to=day.isoformat(), limit=card.MAX_LIST_LIMIT)
        ranked = self._picker.rank(con, [row[_RID] for row in listed.rows])
        result: dict[str, Any] = {
            "day": day.isoformat(), "made_at": datetime.now().isoformat(timespec="seconds"), "plan": self._plan.name,
            "ranking": [self._ranking_row(con, chance) for chance in ranked[:RANKING_COUNT]], "pick": None,
        }
        if ranked:
            result["pick"] = self._pick(con, ranked[0])
        return result

    def _ranking_row(self, con: duckdb.DuckDBPyConnection, chance: RaceChance) -> dict[str, Any]:
        title = card.header_title(card.race_header(con, chance.race_id))
        return {"rid": chance.race_id, "title": title, "timing": chance.timing.label, "probability": round(chance.probability, 4)}

    def _pick(self, con: duckdb.DuckDBPyConnection, chance: RaceChance) -> dict[str, Any]:
        forecast = self._forecaster.forecast(con, chance.race_id, chance.timing)
        ticket_type = TicketType.TRIFECTA if self._plan.ordered else TicketType.TRIO
        odds = AnnouncedComboOdds(con).read(chance.race_id, ticket_type)
        tickets = self._plan.tickets(ForecastHorses().of(forecast), odds) if odds else []
        rows = [{"組": "-".join(map(str, combo)), "掛け金": stake, "オッズ": odds[combo], "払戻の見込み": round(odds[combo] * stake)}
                for combo, stake in tickets]
        note = ("オッズは締め切り前のいちばん新しい断面。発走が近づいて変わったら、もう一度動かして組み直す。" if odds
                else "組ごとのオッズがまだ無いので、買い目は組んでいない。当日（オッズが出てから）もう一度動かす。")
        note = f"{note}{REFERENCE_NOTE}"
        return {
            "rid": chance.race_id, "title": forecast["title"], "timing": forecast["timing"], "probability": round(chance.probability, 4),
            "horses": [self._horse(horse) for horse in forecast["horses"]], "tickets": rows,
            "total_yen": sum(stake for _, stake in tickets), "note": note,
        }

    @staticmethod
    def _horse(horse: dict[str, Any]) -> dict[str, Any]:
        return {"馬番": horse.get(columns.HORSE_NO), "馬名": horse.get(columns.HORSE_NAME), "印": horse.get(columns.MARK),
                "人気": horse.get(columns.POPULARITY), "単勝オッズ": horse.get(columns.WIN_ODDS),
                "3着以内の確率": _rounded(horse.get(columns.PROBABILITY)), "1着の確率": _rounded(horse.get(columns.WIN_PROBABILITY))}


def _rounded(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value
