"""事例の一覧: 10万馬券になったレースを配当の高い順に並べ、崩れた人気馬と来た穴馬の事情を1行ずつ添える。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .popularity_band import FAVORITE
from .runner_circumstances import CIRCUMSTANCES

COLUMNS: tuple[str, ...] = ("日付", "場", "R", "クラス", "頭数", "3連単", "型", "1〜3着の人気", "崩れた人気馬（人気: 事情）", "来た穴馬（人気: 事情）")
#: 事情の文に入れない列（どの馬にもよく付く、または表の別の列で分かるもの）。
_QUIET: frozenset[str] = frozenset({"同じ場から", "前走1〜3番人気", "騎手が場の10位以内", "中1〜2週"})
_LOST_FINISH = 4
_MAX_CIRCUMSTANCES = 4


@dataclass(frozen=True)
class CaseListTable:
    """``runners``（事情の列が付いた出走の行）と ``races``（``race_id`` を index に持ち、配当・型を持つ表）から、一覧の表を作る。"""

    limit: int = 40

    def build(self, runners: pd.DataFrame, races: pd.DataFrame, *, title: str) -> Table:
        top = races.sort_values("trifecta_payout", ascending=False).head(self.limit)
        by_race = {race_id: group for race_id, group in runners[runners["race_id"].isin(top.index)].groupby("race_id")}
        rows = [self._row(race_id, race, by_race.get(race_id, runners.iloc[0:0])) for race_id, race in top.iterrows()]
        return Table.from_records(rows, COLUMNS, title=title,
                                  note="配当の高い順。事情は、馬ごとに付いた事情のうち目立つものを最大4つ。崩れた人気馬 = 1〜3番人気で4着以下。")

    def _row(self, race_id: str, race: pd.Series, group: pd.DataFrame) -> dict:
        placed = group[group["finish"] <= 3].sort_values("finish")
        lost = group[(group["band"] == FAVORITE) & ((group["finish"] >= _LOST_FINISH) | group["finish"].isna())]
        came = placed[placed["band"] != FAVORITE]
        return {
            "日付": race["race_date"], "場": race["venue"], "R": race["race_no"], "クラス": race["class_name"],
            "頭数": race["field_size"], "3連単": f"{int(race['trifecta_payout']):,}円", "型": race["型（順不同）"],
            "1〜3着の人気": "→".join(str(int(p)) for p in placed["popularity"]),
            "崩れた人気馬（人気: 事情）": " ／ ".join(self._describe(h) for _, h in lost.sort_values("popularity").iterrows()),
            "来た穴馬（人気: 事情）": " ／ ".join(self._describe(h) for _, h in came.iterrows()),
        }

    def _describe(self, horse: pd.Series) -> str:
        found = [name for name in CIRCUMSTANCES if name not in _QUIET and bool(horse.get(name, False))]
        text = "・".join(found[:_MAX_CIRCUMSTANCES]) or "目立つ事情なし"
        return f"{int(horse['popularity'])}番人気: {text}"
