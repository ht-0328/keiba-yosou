"""事例の一覧: 荒れたファイナルレースを配当の高い順に並べ、1レースにつき1つの表で、出走馬ごとの人気・オッズ・着順・近走を見せる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table
from 地方の万馬券.analysis.outcome_pattern_table import PATTERN_COUNTS

from .recent_runs_text import RecentRunsText

COLUMNS: tuple[str, ...] = ("着順", "人気", "単勝オッズ", "枠", "性齢", "間隔（日）", "ファイナルの出走/3着以内", "4角", "近走（古い順）")
_MISSING = "—"


@dataclass(frozen=True)
class CaseListTable:
    """``races``（``race_id`` を index に持ち、開催日・条件・配当・型を持つ表）の上から ``limit`` レースを、レースごとの表にする。

    馬名・騎手名は載せない。近走は高知の出走だけ（``RecentRunsText``）。
    """

    limit: int = 20
    recent: RecentRunsText = RecentRunsText()

    def build(self, runs: pd.DataFrame, runners: pd.DataFrame, races: pd.DataFrame) -> list[Table]:
        top = races.sort_values("trifecta_payout", ascending=False).head(self.limit)
        listed = runners[runners["race_id"].isin(top.index)]
        listed = listed.assign(recent_text=self.recent.texts(runs, listed))
        by_race = {race_id: group for race_id, group in listed.groupby("race_id")}
        return [self._race_table(race, by_race[race_id]) for race_id, race in top.iterrows()]

    def _race_table(self, race: pd.Series, horses: pd.DataFrame) -> Table:
        title = (f"{race['race_date']:%Y-%m-%d} {race['class_name']} {int(race['distance_m'])}m {race['condition']} {int(race['field_size'])}頭"
                 f"　3連単 {int(race['trifecta_payout']):,}円　型 {race[PATTERN_COUNTS]}")
        ordered = horses.sort_values(["finish", "popularity"], na_position="last")
        return Table.from_records([self._horse_row(horse) for _, horse in ordered.iterrows()], COLUMNS, title=title)

    def _horse_row(self, horse: pd.Series) -> dict:
        return {
            "着順": _whole(horse["finish"]), "人気": _whole(horse["popularity"]),
            "単勝オッズ": _MISSING if pd.isna(horse["win_odds"]) else f"{horse['win_odds']:.1f}",
            "枠": _whole(horse["frame_no"]), "性齢": f"{horse['sex']}{_whole(horse['age'])}", "間隔（日）": _whole(horse["interval_days"]),
            "ファイナルの出走/3着以内": f"{_whole(horse['final_runs_before'])}/{_whole(horse['final_places_before'])}",
            "4角": _whole(horse["corner4"]), "近走（古い順）": horse["recent_text"],
        }


def _whole(value: object) -> str:
    """整数で書く。値が無ければ「—」。"""
    return _MISSING if pd.isna(value) else str(int(value))
