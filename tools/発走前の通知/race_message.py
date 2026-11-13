"""保存してある中央の1レースの予想と計画から、通知の文（見出し・印・実際に買う買い目）と添付（表の画像・全頭の予想根拠）を作る。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from 共通 import db

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, MARK_REASON, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_VALUE
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.mark_rule import MARK_ORDER, NO_MARK, OUT_MARK
from 今週の予想.race_describer import RaceDescriber
from 今週の予想.race_grades import RaceGrades
from 今週の予想.race_plan import RacePlan

from 発走前の通知.folders import CENTRAL_FOLDER
from 発走前の通知.jra_race_card import JraRaceCard
from 発走前の通知.mark_lines import MarkLines
from 発走前の通知.race_frames import RaceFrames
from 発走前の通知.race_image import RaceImage
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.race_schedule import RaceSchedule
from 発走前の通知.race_styles import RaceStyles
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.tendencies import Tendencies

#: 表の列（予想の JSON の馬の鍵と同じ名前）。印の理由は文の ◎・☆・注・消 の行に添える。
_COLUMNS: tuple[str, ...] = (MARK, HORSE_NO, HORSE_NAME, WIN_ODDS, PROBABILITY, PLACE_VALUE, WIN_VALUE, MARK_REASON)
#: 当日の時点（予想の JSON の timing）。
_RACE_DAY = "当日"


class RaceMessage:
    """文は地方の通知と同じ短い形で、見出し・期待度（◎ の点数の S・A・B・C。画像の見出しにも札）・その日の馬場の傾向（``tendencies``。先に終わった同じ芝ダのレースがあれば）・印の付いた馬（``MarkLines``。◎○▲△☆注消）・実際に買う買い目（``RaceDescriber.bought``。
    買う計画は forecast.py が結果の JSON に書き足した ``plan``）だけ。参考の買い目と ◎ の理由・近走は、添付の全頭の予想根拠で見る。
    添付は、全頭の表の画像（``RaceImage``。推定脚質の列は ``styles``。``reports/発走前の通知/中央/<開催日>/<rid>.png``）と、``ForecastStore`` が書いた
    全頭の予想根拠（``<rid>.md``。あれば）。"""

    def __init__(self, store: ForecastStore | None = None, describer: RaceDescriber | None = None,
                 schedule: RaceSchedule | None = None, frames: RaceFrames | None = None, image: RaceImage | None = None,
                 folder: Path = CENTRAL_FOLDER, tendencies: Tendencies | None = None, styles: RaceStyles | None = None) -> None:
        self._store = store or ForecastStore()
        self._describer = describer or RaceDescriber()
        self._schedule = schedule or RaceSchedule()
        self._frames = frames or RaceFrames(default=db.JRA)
        self._image = image or RaceImage()
        self._folder = Path(folder)
        self._tendencies = tendencies
        self._styles = styles

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        race = self._find(rid)
        tendency = self._tendencies.of(rid, race.venue) if self._tendencies and race else None
        card = self.card(forecast, race, self._frames.read(rid), tendency.text() if tendency else "",
                         self._styles.read(rid) if self._styles else {})
        path = self.image_path(rid)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._image.draw(card).save(path)
        reasons = self._store.reasons_path(rid)
        return RaceNotice(self.describe(card), (path, reasons) if reasons.is_file() else (path,))

    def image_path(self, rid: str) -> Path:
        return self._folder / f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}" / f"{rid}.png"

    def card(self, forecast: dict[str, Any], race: ScheduledRace | None, frames: Mapping[int, int], tendency: str = "",
             styles: Mapping[int, str] | None = None) -> JraRaceCard:
        """予想の JSON（``horses``・``tickets``・``plan``・時点と目安）とレース一覧の行から、通知の中身を組む。"""
        plan = RacePlan.from_dict(forecast["plan"]) if forecast.get("plan") else None
        bets = tuple(self._describer.bought(forecast, plan))
        timing = str(forecast.get("timing", ""))
        grades = RaceGrades.from_dict(forecast)
        return JraRaceCard(heading=f"{race.venue} {race.number}R" if race else str(forecast["title"]),
                           name=race.name if race else "", post=f"{race.post:%H:%M} 発走" if race else "",
                           timing=f"{timing}の時点", race_day=timing == _RACE_DAY, grades=grades.text(),
                           table=self._table(forecast), frames=dict(frames), bets=bets, notes=() if bets else self._notes(plan),
                           tendency=tendency, styles=dict(styles or {}), grade_badge=grades.badge())

    def describe(self, card: JraRaceCard) -> str:
        """通知の文: 見出し・期待度・馬場の傾向（あれば）・印の付いた馬（1つの印につき1行）・実際に買う買い目。"""
        lines = [f"**{card.title}** 中央の予想・{card.timing}", card.grades, *([card.tendency] if card.tendency else []),
                 *MarkLines().lines(card.table)]
        if not card.bets:
            return "\n".join([*lines, f"買い目: なし（{'。'.join(card.notes)}）" if card.notes else "買い目: なし"])
        return "\n".join([*lines, f"買い目（合計 {card.yen:,}円）:", *(f"- {line}" for line, _ in card.bets)])

    @staticmethod
    def _notes(plan: RacePlan | None) -> tuple[str, ...]:
        """買わないときの理由（複勝の参加の種類の理由と、単勝・馬単を買わない理由）。"""
        if plan is None:
            return ("買う計画が無い（財布かオッズが無い）",)
        return tuple(reason for reason in (plan.reason, plan.ticket_reason) if reason)

    @staticmethod
    def _table(forecast: dict[str, Any]) -> pd.DataFrame:
        """印の順（◎○▲△☆注消、最後に無印）。同じ印の中は 3着以内の確率の高い順。危険な人気馬でない消（前の版の予想）は無印にする。"""
        rows = [{**{column: horse.get(column) for column in _COLUMNS},
                 MARK: NO_MARK if horse["mark"] == OUT_MARK and not horse.get("is_danger") else horse["mark"]}
                for horse in forecast["horses"]]
        table = pd.DataFrame(rows, columns=list(_COLUMNS))
        order = table[MARK].map({mark: index for index, mark in enumerate(MARK_ORDER)}).fillna(len(MARK_ORDER))
        return table.assign(_order=order).sort_values(["_order", PROBABILITY], ascending=[True, False]).drop(columns="_order")

    def _find(self, rid: str) -> ScheduledRace | None:
        day = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
        return next((race for race in self._schedule.read(day) if race.rid == rid), None)
