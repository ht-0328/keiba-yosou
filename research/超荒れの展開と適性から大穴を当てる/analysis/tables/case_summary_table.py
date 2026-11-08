"""選んだ事例の来た大穴について、展開・馬場・斤量の形ごとに頭数を数える表（1レースずつ見た結果を数で確かめる）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from .cells import percent


def _bias_match(rows: pd.DataFrame) -> pd.Series:
    """その日の内外の傾き（±0.1 を超えたとき）と枠の側が合っていたか。"""
    inner, side = rows["tilt_inner"], rows["horse_side"]
    return pd.Series(np.select([(inner > 0.1) & (side == "内"), (inner < -0.1) & (side == "外"), inner.abs() > 0.1],
                               ["傾きと同じ側", "傾きと同じ側", "傾きと逆か中"], default="傾きが小さい日"), index=rows.index)


#: 数える見方（見出し → 1頭の行から値を作る関数）。
VIEWS = {
    "結果の脚質": lambda r: r["result_style"].fillna("（不明）"),
    "4コーナーの位置": lambda r: r["corner4_group"].fillna("（不明）"),
    "上がりの順位": lambda r: pd.cut(r["last3f_rank"], [0, 3, 6, 30], labels=["1〜3位", "4〜6位", "7位以下"]).astype(str),
    "いつもとの位置の差": lambda r: r["position_shift"].fillna("（近走なし）"),
    "推定脚質（レース前）": lambda r: r["style_before"].fillna("（なし）"),
    "結果のペース": lambda r: r["pace"].fillna("（不明）"),
    "予想との違い": lambda r: r["pace_vs_forecast"].fillna("（予想なし）"),
    "枠の側とその日の内外の傾き": _bias_match,
    "コースの実績": lambda r: np.where(r["course_places_before"] > 0, "同じコースで3着以内あり", "なし"),
    "斤量（平均との差）": lambda r: np.select([r["carried_vs_mean"] <= -1, r["carried_vs_mean"] >= 1], ["軽い", "重い"], default="平均並み"),
    "前走との斤量の差": lambda r: np.select([r["carried_change"] <= -1, r["carried_change"] >= 1, r["carried_change"].notna()],
                                    ["軽くなった", "重くなった", "同じ"], default="前走なし"),
    "重量種別": lambda r: r["weight_type"],
}


@dataclass(frozen=True)
class CaseSummaryTable:
    """``runners`` の、``groups``（見出し → 選んだ race_id の並び）のレースの来た大穴を数える。1番人気の着順も添える。"""

    def build(self, runners: pd.DataFrame, groups: dict[str, list[str]], title: str) -> Table:
        parts = {name: runners.loc[runners["race_id"].isin(ids) & runners["longshot"] & (runners["top3"] > 0)] for name, ids in groups.items()}
        rows = []
        for view, make in VIEWS.items():
            values = {name: pd.Series(make(part), index=part.index) for name, part in parts.items()}
            labels = sorted(set().union(*[set(series.astype(str)) for series in values.values()]))
            for label in labels:
                cells = [f"{int((series.astype(str) == label).sum())}（{percent((series.astype(str) == label).sum(), len(series))}）"
                         for series in values.values()]
                rows.append([view, label, *cells])
        favorite_cells = []
        for ids in groups.values():
            favorites = runners.loc[runners["race_id"].isin(ids) & (runners["popularity"] == 1)]
            favorite_cells.append(f"{int((favorites['finish'] > 3).sum())} / {len(favorites)}レース")
        rows.append(["1番人気の着順", "4着以下", *favorite_cells])
        columns = ["見方", "値", *[f"{name}（来た大穴 {len(part)}頭）" for name, part in parts.items()]]
        return Table(columns, rows, title=title, note="来た大穴 = 3着以内に入った10番人気以下の馬。（ ）はその事例の来た大穴の中の割合。")
