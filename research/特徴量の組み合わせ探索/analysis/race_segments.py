"""レースの区分（芝・短距離、東京・ダートなど）。区分の段ごとに、全レースを重なりなく分ける。"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.feature.value_types import as_numbers

#: 距離帯（両端を含む m）。custom_binary の conditions の 距離: {min, max} にそのまま書ける。
DISTANCE_BANDS = {"短距離": (None, 1400), "マイル": (1401, 1800), "中距離": (1801, 2200), "長距離": (2201, None)}
#: 区分の段。各段は、ここに並べた列の値の組でレースを分ける。
LEVELS = {
    "全レース": (),
    "芝ダ": ("芝ダ",),
    "芝ダ×距離帯": ("芝ダ", "距離帯"),
    "芝ダ×馬場状態": ("芝ダ", "馬場状態"),
    "競馬場×芝ダ": ("競馬場", "芝ダ"),
    "競馬場×芝ダ×距離帯": ("競馬場", "芝ダ", "距離帯"),
}


@dataclass(frozen=True)
class RaceSegments:
    """``codes`` は段ごとの区分の番号（行ごと）、``labels`` は段ごとの 番号 → (名前, conditions の辞書)。"""

    codes: dict[str, np.ndarray]
    labels: dict[str, dict[int, tuple[str, dict]]]

    @classmethod
    def of(cls, frame: pd.DataFrame) -> "RaceSegments":
        keys = pd.DataFrame({
            "芝ダ": frame["芝ダ"].astype(str), "競馬場": frame["競馬場"].astype(str),
            "馬場状態": frame["馬場状態"].astype(str), "距離帯": distance_band(frame["距離"]),
        }, index=frame.index)
        codes, labels = {}, {}
        for level, columns in LEVELS.items():
            if not columns:
                codes[level] = np.zeros(len(frame), dtype=np.int64)
                labels[level] = {0: ("全レース", {})}
                continue
            groups = keys.groupby(list(columns), sort=True, observed=True).ngroup()
            codes[level] = groups.to_numpy()
            firsts = keys.assign(code=groups).drop_duplicates("code").set_index("code")
            labels[level] = {code: segment_label(firsts.loc[code], columns) for code in firsts.index}
        return cls(codes, labels)


def distance_band(distance: pd.Series) -> pd.Series:
    meters = as_numbers(distance)
    return pd.Series(
        np.select([meters <= 1400, meters <= 1800, meters <= 2200], ["短距離", "マイル", "中距離"], "長距離"),
        index=distance.index,
    )


def segment_label(row: pd.Series, columns: tuple[str, ...]) -> tuple[str, dict]:
    """区分の名前と、custom_binary の conditions に書く辞書。"""
    conditions = {}
    for column in columns:
        if column == "距離帯":
            low, high = DISTANCE_BANDS[row[column]]
            conditions["距離"] = {key: value for key, value in (("min", low), ("max", high)) if value is not None}
        else:
            conditions[column] = [row[column]]
    return "・".join(str(row[column]) for column in columns), conditions
