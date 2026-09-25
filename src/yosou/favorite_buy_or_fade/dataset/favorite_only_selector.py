"""学習データ・予測用データに入れる行を選ぶ（1番人気だけ）。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter
from yosou.shared.feature import as_numbers

#: この予想が対象にする人気。
_FAVORITE = 1


class FavoriteOnlySelector:
    """1番人気の行だけを学習データ・予測用データに残す。``SampleSelector`` を守る。

    1番人気でない行も、いったんは残して返す。レース内順位の特徴量（まとまり G）を、そのレースの全出走馬から
    計算するためである。1番人気だけに絞るのは、特徴量を作ったあとの ``keep_samples()`` になる。
    """

    def __init__(self) -> None:
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。``train_first_day`` より前（ウォームアップ期間）の行は入れない。
        人気は確定単勝人気を使う。
        """
        runners = self._flat_runners.apply(entries)
        return runners[runners["race_date"] >= pd.Timestamp(train_first_day)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。障害レースと、人気が分からないレースは ``ValueError``。出走馬がいなければ ``LookupError``。"""
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        if runners["popularity"].isna().all():
            raise ValueError(f"人気が分かりません。--pops 馬番:人気 か --odds で渡してください: {race_id}")
        return runners

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。1番人気の行だけ。"""
        return rows[as_numbers(rows["popularity"]) == _FAVORITE]
