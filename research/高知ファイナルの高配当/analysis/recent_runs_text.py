"""近走の文: 馬ごとに、そのレースより前の高知の出走を古い順に1走ずつ短い文にして並べる（事例を1頭ずつ読むため）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .final_race import FINAL

_SEPARATOR = " ／ "
_NONE = "（高知での出走なし）"
_MISSING = "—"
#: ファイナルレースだった走の頭に付ける印。
_FINAL_MARK = "F "


@dataclass(frozen=True)
class RecentRunsText:
    """1走は「クラス 距離: 人気・着順（着差・4コーナーの順位）」。ファイナルレースだった走は頭に F を付ける。"""

    count: int = 5

    def texts(self, runs: pd.DataFrame, runners: pd.DataFrame) -> pd.Series:
        """``runs``（馬ごとに古い順の高知の全出走）から、``runners`` の各行の馬の近走の文（``runners`` と同じ index）。"""
        history = runs[runs["horse_id"].isin(runners["horse_id"])]
        by_horse = {horse_id: group for horse_id, group in history.groupby("horse_id")}
        texts = [self._text(by_horse[horse_id], day) for horse_id, day in zip(runners["horse_id"], runners["race_date"])]
        return pd.Series(texts, index=runners.index, dtype="object")

    def _text(self, horse_runs: pd.DataFrame, day: pd.Timestamp) -> str:
        before = horse_runs[horse_runs["race_date"] < day].tail(self.count)
        return _SEPARATOR.join(self._one(run) for _, run in before.iterrows()) or _NONE

    def _one(self, run: pd.Series) -> str:
        mark = _FINAL_MARK if run[FINAL] else ""
        gap = _MISSING if pd.isna(run["time_diff"]) else f"{run['time_diff']:+.1f}"
        return (f"{mark}{run['class_name']} {_whole(run['distance_m'])}m: {_whole(run['popularity'])}人{_whole(run['finish'])}着"
                f"（{gap}・4角{_whole(run['corner4'])}）")


def _whole(value: object) -> str:
    """整数で書く。値が無ければ「—」。"""
    return _MISSING if pd.isna(value) else str(int(value))
