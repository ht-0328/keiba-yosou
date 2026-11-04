"""レースの条件の表: 10万馬券になったレースと全レースで、レースの条件（頭数・クラス・競馬場・距離・馬場・人気の偏り・遠征馬の数 など）の割合を比べる。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

COLUMNS: tuple[str, ...] = ("条件", "値", "事象のレース数", "事象での割合", "全レース数", "全レースでの割合", "倍率")
#: 1番人気の単勝オッズの帯。
_FAVORITE_ODDS_BINS = [0, 1.9, 2.9, 4.9, np.inf]
_FAVORITE_ODDS_LABELS = ["〜1.9倍", "2.0〜2.9倍", "3.0〜4.9倍", "5.0倍〜"]
#: 1〜3番人気の単勝支持率の合計の帯。
_TOP3_SUPPORT_BINS = [0, 0.55, 0.70, 1.01]
_TOP3_SUPPORT_LABELS = ["55%未満", "55〜70%", "70%以上"]
_DISTANCE_BINS = [0, 1200, 1600, 1900, np.inf]
_DISTANCE_LABELS = ["〜1200m", "1300〜1600m", "1700〜1900m", "2000m〜"]
_HEADS_BINS = [0, 12, 14, np.inf]
_HEADS_LABELS = ["11〜12頭", "13〜14頭", "15頭〜"]
_COUNT_BINS = [-1, 0, 2, np.inf]
_COUNT_LABELS = ["0頭", "1〜2頭", "3頭以上"]
#: クラス名 → 帯。
_CLASS_BANDS: dict[str, str] = {
    "新馬": "新馬・未勝利・年齢の条件戦", "未勝利": "新馬・未勝利・年齢の条件戦", "年齢の条件戦": "新馬・未勝利・年齢の条件戦",
    "C4": "C", "C3": "C", "C2": "C", "C": "C", "C1": "C", "B4": "B", "B3": "B", "B2": "B", "B": "B", "B1": "B",
    "A4": "A・オープン", "A3": "A・オープン", "A2": "A・オープン", "A": "A・オープン", "A1": "A・オープン", "オープン": "A・オープン",
    "準重賞": "重賞", "重賞": "重賞", "Jpn3": "重賞", "Jpn2": "重賞", "Jpn1": "重賞",
}


@dataclass(frozen=True)
class RaceConditionTable:
    """出走の表（事情の列が付いたもの）をレース単位にまとめ、事象のレース（``event_race_ids``）と全レースで条件ごとの割合を比べる。"""

    def race_table(self, runners: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レースの条件の表。"""
        first = runners.groupby("race_id").first()
        grouped = runners.groupby("race_id")
        support = self._support(runners)
        table = pd.DataFrame({
            "頭数": pd.cut(first["field_size"], _HEADS_BINS, labels=_HEADS_LABELS),
            "クラス": first["class_name"].map(_CLASS_BANDS).fillna("不明"),
            "競馬場": first["venue"],
            "距離": pd.cut(first["distance_m"], _DISTANCE_BINS, labels=_DISTANCE_LABELS),
            "馬場": first["condition"],
            "1番人気のオッズ": pd.cut(grouped["win_odds"].min(), _FAVORITE_ODDS_BINS, labels=_FAVORITE_ODDS_LABELS),
            "1〜3番人気の支持率": pd.cut(support, _TOP3_SUPPORT_BINS, labels=_TOP3_SUPPORT_LABELS),
            "遠征馬の数": pd.cut(grouped["遠征"].sum(), _COUNT_BINS, labels=_COUNT_LABELS),
            "転入初戦の数": pd.cut(grouped["転入初戦"].sum(), _COUNT_BINS, labels=_COUNT_LABELS),
            "中央所属の数": pd.cut(grouped["中央所属"].sum(), _COUNT_BINS, labels=_COUNT_LABELS),
            "前走で前にいた馬の数": pd.cut(grouped["前走は前にいた"].sum(), [-1, 1, 3, np.inf], labels=["0〜1頭", "2〜3頭", "4頭以上"]),
            "連闘の数": pd.cut(grouped["連闘"].sum(), _COUNT_BINS, labels=_COUNT_LABELS),
            "牝馬限定": np.where(first["mixed_sex"].astype("boolean").fillna(True), "混合", "牝馬限定"),
            "2歳戦": np.where(grouped["age"].max() <= 2, "2歳戦", "3歳以上"),
        })
        return table

    def build(self, race_table: pd.DataFrame, event_race_ids: pd.Index, *, title: str) -> Table:
        event = race_table.loc[race_table.index.isin(event_race_ids)]
        rows = []
        for condition in race_table.columns:
            rows.extend(self._condition_rows(condition, event[condition], race_table[condition]))
        return Table.from_records(rows, COLUMNS, title=title, note="倍率 = 事象での割合 ÷ 全レースでの割合。1 より大きい値は、その条件のレースで事象が起きやすい。")

    def _condition_rows(self, condition: str, event: pd.Series, base: pd.Series) -> list[dict]:
        event_counts = event.astype("string").value_counts()
        base_counts = base.astype("string").value_counts()
        rows = []
        for value, base_n in base_counts.items():
            event_n = int(event_counts.get(value, 0))
            event_share, base_share = event_n / max(len(event), 1), base_n / max(len(base), 1)
            rows.append({"条件": condition, "値": value, "事象のレース数": event_n, "事象での割合": f"{event_share:.1%}",
                         "全レース数": int(base_n), "全レースでの割合": f"{base_share:.1%}",
                         "倍率": round(event_share / base_share, 2) if base_share else float("nan")})
        return rows

    def _support(self, runners: pd.DataFrame) -> pd.Series:
        """1〜3番人気の単勝支持率（1/オッズ をレース内で合計 1 にしたもの）の合計。"""
        inverse = 1.0 / runners["win_odds"].replace(0, np.nan)
        share = inverse / inverse.groupby(runners["race_id"]).transform("sum")
        top3 = share.where(runners["popularity"] <= 3, 0.0)
        return top3.groupby(runners["race_id"]).sum()
