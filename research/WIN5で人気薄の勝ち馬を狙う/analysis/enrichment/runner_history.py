"""馬ごとの過去走から、事実表に無い「前の走の様子」と「これまでの実績」の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: 前の走からそのまま写す列（事実表の列 → 足す列）。
_SHIFTED: dict[str, str] = {
    "class_order": "prev_class_order", "condition": "prev_condition", "frame_no": "prev_frame", "jockey_code": "prev_jockey",
    "blinker": "prev_blinker", "interval_days": "prev_interval", "style": "prev_style",
}
#: 近走の最高着順を見る走の数。
RECENT_RUNS = 5
#: 「好走」とみなす着順。
PLACED = 3
#: 前で運ぶ脚質と、後ろから運ぶ脚質（レース後の判定）。
_FRONT = ("逃げ", "先行")
_BACK = ("差し", "追込")


@dataclass(frozen=True)
class RunnerHistory:
    """出走の表（障害も含む全部の出走）に、今回より前の走だけから作った列を足す。どれもレースの前に分かる値。

    足す列: 前の走のクラス・馬場状態・枠・騎手・ブリンカー・間隔・脚質、2走前の着順、近5走の最高着順、
    これまでに3着以内に入った最高のクラス、勝った最高のクラス、今回の芝ダでの出走数と3着以内の数、今回の芝ダ・馬場（良か道悪か）での3着以内の数、
    逃げ・先行で3着以内に入った回数と、差し・追込で3着以内に入った回数（全部の過去走と、近5走）。
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.sort_values(["horse_id", "race_date", "race_id"]).reset_index(drop=True)
        frame["going"] = np.where(frame["condition"] == "良", "良", "道悪")
        horse = frame.groupby("horse_id", sort=False)
        for source, target in _SHIFTED.items():
            frame[target] = horse[source].shift()
        frame["prev2_finish"] = horse["finish"].shift(2)
        frame["best_recent_finish"] = self._recent_best(frame)
        frame["best_placed_class"] = self._best_class(frame, frame["finish"] <= PLACED)
        frame["best_win_class"] = self._best_class(frame, frame["finish"] == 1)
        frame["surface_runs_before"] = frame.groupby(["horse_id", "surface"], sort=False).cumcount()
        frame["surface_places_before"] = self._places_before(frame, ["horse_id", "surface"])
        frame["going_places_before"] = self._places_before(frame, ["horse_id", "surface", "going"])
        frame["front_places_before"] = self._styled_places_before(frame, _FRONT)
        frame["back_places_before"] = self._styled_places_before(frame, _BACK)
        frame["recent_front_places"] = self._recent_styled_places(frame, _FRONT)
        frame["recent_back_places"] = self._recent_styled_places(frame, _BACK)
        return frame

    @staticmethod
    def _recent_styled_places(frame: pd.DataFrame, styles: tuple[str, ...]) -> pd.Series:
        """近5走（今回より前）のうち、脚質が ``styles`` のどれかで3着以内に入った回数。"""
        placed = (frame["style"].isin(styles) & (frame["finish"] <= PLACED)).astype(float)
        previous = placed.groupby(frame["horse_id"], sort=False).shift().fillna(0.0)
        rolling = previous.groupby(frame["horse_id"], sort=False).rolling(RECENT_RUNS, min_periods=1).sum()
        return rolling.reset_index(level=0, drop=True).sort_index()

    @staticmethod
    def _styled_places_before(frame: pd.DataFrame, styles: tuple[str, ...]) -> pd.Series:
        """今回より前に、脚質が ``styles`` のどれかで3着以内に入った回数。"""
        placed = (frame["style"].isin(styles) & (frame["finish"] <= PLACED)).astype(float)
        return placed.groupby(frame["horse_id"], sort=False).cumsum() - placed

    @staticmethod
    def _recent_best(frame: pd.DataFrame) -> pd.Series:
        previous = frame.groupby("horse_id", sort=False)["finish"].shift()
        rolling = previous.groupby(frame["horse_id"], sort=False).rolling(RECENT_RUNS, min_periods=1).min()
        return rolling.reset_index(level=0, drop=True).sort_index()

    @staticmethod
    def _best_class(frame: pd.DataFrame, achieved: pd.Series) -> pd.Series:
        """今回より前に ``achieved`` を満たした走のクラスの最高（無ければ欠損値）。"""
        value = frame["class_order"].where(achieved.fillna(False), -1.0)
        previous = value.groupby(frame["horse_id"], sort=False).shift().fillna(-1.0)
        best = previous.groupby(frame["horse_id"], sort=False).cummax()
        return best.where(best >= 0)

    @staticmethod
    def _places_before(frame: pd.DataFrame, keys: list[str]) -> pd.Series:
        placed = (frame["finish"] <= PLACED).astype(float)
        return placed.groupby([frame[key] for key in keys], sort=False).cumsum() - placed
