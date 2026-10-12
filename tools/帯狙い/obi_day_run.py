"""1日の帯狙い: 荒れるレースを選び、荒れる前提の予想で予想し、1万円の買い目を組む。"""

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
from 帯狙い.obi_day_picker import DEFAULT_LINE, ObiDayPicker, RaceChance

#: 買い目が参考であることの注記（研究「百万馬券を当てる」の docs/06 の 3。まだ見ていない期間での確かめが無いため）。
REFERENCE_NOTE = "買い目は参考（財布にも買い目の記録にも書かない）。"
#: 結果に残す、荒れそうなレースの上位の数。
RANKING_COUNT = 10
#: 出馬表の一覧の rid の列。
_RID = card.CARD_LIST_HEADERS.index("rid")


class ObiDayRun:
    """1日の帯狙いを進める（ほかを順に呼ぶだけ）。

    1. その日のレースを、3連単が 1,000倍以上になる確率の高い順に並べる（``ObiDayPicker``）。線以上のレースを全部選ぶ（1日何レースでも）。
    2. 選んだレースを、荒れる前提のモデルの置き場所を渡した ``RaceForecaster`` で予想する（印・危険な人気馬の判定も今週の予想と同じ）。
       同じレースを、今の予想のモデルの置き場所を渡した ``usual_forecaster`` でも予想する（2着・3着の重みに使う）。
    3. 3着以内と1着の確率と、締め切り前（なければ確定）の組ごとのオッズで、``plan`` の買い目を組む。
       オッズがまだ無ければ（木曜・前日でオッズの無いレース）、買い目は組まず、当日に組み直すことを書く。
    結果は JSON にできる辞書。
    """

    def __init__(self, picker: ObiDayPicker, forecaster: RaceForecaster, usual_forecaster: RaceForecaster | None,
                 plan: TicketPlan, line: float = DEFAULT_LINE) -> None:
        self._picker = picker
        self._forecaster = forecaster
        self._usual_forecaster = usual_forecaster
        self._plan = plan
        self._line = line

    def run(self, con: duckdb.DuckDBPyConnection, day: date) -> dict[str, Any]:
        listed = card.list_cards(con, date_from=day.isoformat(), date_to=day.isoformat(), limit=card.MAX_LIST_LIMIT)
        ranked = self._picker.rank(con, [row[_RID] for row in listed.rows])
        chosen = self._picker.above(ranked, self._line)
        return {
            "day": day.isoformat(), "made_at": datetime.now().isoformat(timespec="seconds"), "plan": self._plan.name, "line": self._line,
            "ranking": [self._ranking_row(con, chance) for chance in ranked[:RANKING_COUNT]],
            "picks": [self._pick(con, chance) for chance in chosen],
        }

    def _ranking_row(self, con: duckdb.DuckDBPyConnection, chance: RaceChance) -> dict[str, Any]:
        title = card.header_title(card.race_header(con, chance.race_id))
        return {"rid": chance.race_id, "title": title, "timing": chance.timing.label, "probability": round(chance.probability, 4),
                "chosen": chance.probability >= self._line}

    def _pick(self, con: duckdb.DuckDBPyConnection, chance: RaceChance) -> dict[str, Any]:
        forecast = self._forecaster.forecast(con, chance.race_id, chance.timing)
        usual = self._usual_forecaster.forecast(con, chance.race_id, chance.timing) if self._usual_forecaster is not None else None
        ticket_type = TicketType.TRIFECTA if self._plan.ordered else TicketType.TRIO
        odds = AnnouncedComboOdds(con).read(chance.race_id, ticket_type)
        tickets = self._plan.tickets(ForecastHorses().of(forecast, usual), odds) if odds else []
        rows = [{"組": "-".join(map(str, combo)), "掛け金": stake, "オッズ": odds[combo], "払戻の見込み": round(odds[combo] * stake)}
                for combo, stake in tickets]
        note = ("オッズは締め切り前のいちばん新しい断面。発走が近づいて変わったら、もう一度動かして組み直す。" if odds
                else "組ごとのオッズがまだ無いので、買い目は組んでいない。当日（オッズが出てから）もう一度動かす。")
        usual_top3 = self._usual_top3(usual)
        return {
            "rid": chance.race_id, "title": forecast["title"], "timing": forecast["timing"], "probability": round(chance.probability, 4),
            "horses": [self._horse(horse, usual_top3) for horse in forecast["horses"]], "tickets": rows,
            "total_yen": sum(stake for _, stake in tickets), "note": f"{note}{REFERENCE_NOTE}",
        }

    @staticmethod
    def _usual_top3(usual: dict[str, Any] | None) -> dict[int, Any]:
        """今の予想の 馬番 → 3着以内の確率（無ければ空）。"""
        if usual is None:
            return {}
        return {int(horse[columns.HORSE_NO]): horse.get(columns.PROBABILITY)
                for horse in usual["horses"] if horse.get(columns.HORSE_NO) is not None}

    @staticmethod
    def _horse(horse: dict[str, Any], usual_top3: dict[int, Any]) -> dict[str, Any]:
        number = horse.get(columns.HORSE_NO)
        return {"馬番": number, "馬名": horse.get(columns.HORSE_NAME), "印": horse.get(columns.MARK),
                "人気": horse.get(columns.POPULARITY), "単勝オッズ": horse.get(columns.WIN_ODDS),
                "3着以内の確率": _rounded(horse.get(columns.PROBABILITY)), "1着の確率": _rounded(horse.get(columns.WIN_PROBABILITY)),
                "今の予想の3着以内の確率": _rounded(usual_top3.get(int(number))) if number is not None else None}


def _rounded(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value
