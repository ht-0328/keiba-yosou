"""前半の予想（①〜③）の、モデルによらない簡単な基準。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

from ..dataset import label_names as names

#: 基準に使う特徴量の列。
LEAD_RATE, STYLE, PREVIOUS_POSITION, LEAD_CANDIDATES = "先頭率", "推定脚質", "前走の序盤の位置", "逃げそうな馬の数"
#: 推定脚質の「逃げ」。
_FRONT_RUNNER = "逃げ"
#: 3区分の、欠けたクラスに入れる小さな割合（ログを取れるように）。
_FLOOR = 1e-3
#: 逃げそうな馬の数の区切り（3頭以上はまとめる）。
_MAX_CANDIDATES = 3
_CLASSES = list(names.THREE_CLASSES)


class StageBaselines:
    """設計書 16 の 3 の「比べる基準」を、年ごとの確かめの表で出す。割合の表は、その年より前の年の行だけで数える。

    - ① 先頭率をそろえただけ: 過去の先頭率（K）を、レースの中で合計 1 に割り直したもの。
    - ① 推定脚質: 推定脚質が逃げの馬に確率を等分する（逃げの馬がいなければ全馬に等分）。
    - ② 前年までの割合 / 前走の区分からの割合、③ 前年までの割合 / 逃げそうな馬の数からの割合。
    """

    def leader_by_rate(self, horses: pd.DataFrame) -> pd.Series:
        rate = as_numbers(horses[LEAD_RATE]).fillna(0.0)
        return rate / rate.groupby(horses["race_id"]).transform("sum")

    def leader_by_style(self, horses: pd.DataFrame) -> pd.Series:
        race = horses["race_id"]
        front = (horses[STYLE].astype(str) == _FRONT_RUNNER).astype("float64")
        count = front.groupby(race).transform("sum")
        field = race.groupby(race).transform("size")
        share = np.where(count > 0, front / count.where(count > 0, 1.0), 1.0 / field)
        clipped = pd.Series(np.clip(share, _FLOOR, 1.0), index=horses.index)
        return clipped / clipped.groupby(race).transform("sum")

    def prior(self, before: pd.DataFrame, label: str, rows: int) -> np.ndarray:
        """その年より前の行の、クラスの割合を、全部の行に同じ確率として配る（行数 × 3）。"""
        share = before[label].value_counts(normalize=True).reindex(_CLASSES, fill_value=_FLOOR).to_numpy()
        return np.tile(share, (rows, 1))

    def by_key(self, before: pd.DataFrame, target: pd.DataFrame, key: str, label: str) -> np.ndarray:
        """その年より前の行で、鍵の値ごとのクラスの割合を数え、対象の行に配る（鍵の値が無ければ全体の割合）。"""
        table = pd.crosstab(before[key], before[label], normalize="index").reindex(columns=_CLASSES, fill_value=_FLOOR)
        overall = self.prior(before, label, 1)[0]
        found = table.reindex(target[key]).to_numpy()
        return np.where(np.isnan(found).any(axis=1, keepdims=True), overall, found)

    def previous_zone(self, horses: pd.DataFrame) -> pd.Series:
        """前走の序盤の位置の区分（無ければ −1）。"""
        position = as_numbers(horses[PREVIOUS_POSITION])
        zone = np.select([position <= 1 / 3, position <= 2 / 3, position > 2 / 3], [0, 1, 2], default=-1)
        return pd.Series(zone, index=horses.index)

    def candidate_bucket(self, races: pd.DataFrame) -> pd.Series:
        """逃げそうな馬の数（0・1・2・3以上）。"""
        return as_numbers(races[LEAD_CANDIDATES]).fillna(0).clip(upper=_MAX_CANDIDATES)
