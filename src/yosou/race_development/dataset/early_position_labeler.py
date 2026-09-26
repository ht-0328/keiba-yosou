"""① 先頭と ② 序盤の位置の目的変数を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from ..feature.history import EarlyPosition
from . import label_names as names


class EarlyPositionLabeler:
    """① 先頭（1/0）と ② 序盤の位置の区分（0〜2）を付ける（設計書 06 の図1・10 の 2.・3.）。

    値は事実表の列から読む。最初のコーナーの順位（``first_corner_rank``）は、コーナーを5回以上通るレースと直線コースでは
    欠損値になっている。先頭の馬番（``first_corner_leader_no``）は、1頭に決まるレースだけ入っている。
    評価用に、区分に分ける前の序盤の位置（0〜1）も返す。
    """

    def __init__(self) -> None:
        self._early_position = EarlyPosition()

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """列は ``先頭``・``序盤の位置の区分``・``序盤の位置``。行の並びと index は ``samples`` と同じ。"""
        position = self._early_position.of(samples["first_corner_rank"], samples["field_size"])
        leader_no = as_numbers(samples["first_corner_leader_no"])
        is_leader = (as_numbers(samples["horse_no"]) == leader_no).astype("float64")
        return pd.DataFrame({
            names.LEADER: is_leader.where(leader_no.notna()),
            names.EARLY_ZONE: self._early_position.zone_of(position),
            names.EARLY_POSITION: position,
        }, index=samples.index)
