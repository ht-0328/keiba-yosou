"""馬体重の増減・前走からの間隔・馬齢を、表の帯に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

from . import names


class WeightBands:
    """設計書「買うレースと買い目を決める」06 の 2 の帯。

    - 増減: −10kg以下 / −9〜−4kg / −3〜+3kg / +4〜+9kg / +10kg以上
    - 前走からの間隔: 中3週以内（28日以内）/ 4〜9週（29〜70日）/ 10週以上（71日以上。休み明け）
    - 馬齢: 2〜3歳 / 4歳以上

    増減か間隔か馬齢の無い馬（初出走・馬体重の未発表など）の帯は欠損値。例: 3歳・中2週・−12kg なら（−10kg以下, 中3週以内, 2〜3歳）。
    """

    def of(self, weight_change: pd.Series, interval_days: pd.Series, age: pd.Series) -> pd.DataFrame:
        """列は ``BANDS``。行の並びと index は ``weight_change`` と同じ。"""
        change, interval, years = as_numbers(weight_change), as_numbers(interval_days), as_numbers(age)
        return pd.DataFrame({
            names.CHANGE_BAND: self._band(change, [-9.5, -3.5, 3.5, 9.5], names.CHANGE_BANDS),
            names.INTERVAL_BAND: self._band(interval, [28.5, 70.5], names.INTERVAL_BANDS),
            names.AGE_BAND: self._band(years, [3.5], names.AGE_BANDS),
        }, index=weight_change.index)

    def _band(self, values: pd.Series, edges: list[float], labels: tuple[str, ...]) -> pd.Series:
        position = np.searchsorted(np.asarray(edges), values.to_numpy(dtype="float64"), side="left")
        band = pd.Series(np.asarray(labels, dtype=object)[np.clip(position, 0, len(labels) - 1)], index=values.index, dtype="object")
        return band.where(values.notna())
