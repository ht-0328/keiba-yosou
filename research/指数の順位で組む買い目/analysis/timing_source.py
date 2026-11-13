"""時点（当日・前日）ごとの、予測と比べる相手の置き場所。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TimingSource:
    """1つの時点の材料。``top3``・``win`` は半年ごとに学び直した区切りごとの予測（研究「複勝以外の回収率100超」が書いたもの）、
    ``baseline`` は道具「印の成績」が同じ予測に今の印を付けて組んだ買い目の CSV。どれも reports からの相対パス。"""

    label: str
    top3: str
    win: str
    baseline: str
    note: str

    def top3_path(self, reports: Path) -> Path:
        return reports / self.top3

    def win_path(self, reports: Path) -> Path:
        return reports / self.win

    def baseline_path(self, reports: Path) -> Path:
        return reports / self.baseline


#: 当日は 2015年から、前日は 2019年からの区切りごとの予測がある。前日の比べる相手は、道具「印の成績」の既定（2023〜2026年のテスト期間）の買い目。
TIMINGS: dict[str, TimingSource] = {
    "当日": TimingSource(
        "当日",
        "複勝以外の回収率100超/predictions-2015から/dscore_race_day/top3-race_day.pkl",
        "複勝以外の回収率100超/predictions-2015から/dscore_finish_race_day/win-race_day.pkl",
        "複勝以外の回収率100超/印の成績-2015から/買い目/dscore_race_day_top3-race_day.csv",
        "当日の予測（2015年〜）と、同じ予測に今の印を付けた買い目",
    ),
    "前日": TimingSource(
        "前日",
        "複勝以外の回収率100超/predictions-2019から/dscore_day_before/top3-day_before.pkl",
        "複勝以外の回収率100超/predictions-2019から/dscore_day_before/win-day_before.pkl",
        "印の成績/買い目/h2h_ability_h2h-day_before.csv",
        "前日の予測（2019年〜）と、道具「印の成績」の既定の前日の買い目（テスト期間は 2023年〜）",
    ),
}
