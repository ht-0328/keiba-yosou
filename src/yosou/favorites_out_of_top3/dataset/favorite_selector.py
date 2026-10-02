"""学習データ・予測用データに入れる行を選び、「人気馬か」を足す。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter

from .column_names import FAVORITE_BAND, IS_FAVORITE
from .favorite_band import FavoriteBand
from .favorite_rule import FavoriteRule


class FavoriteSelector:
    """入れる行を選ぶ（設計書 06 の図1）。``SampleSelector`` を守る。

    人気馬でない行も、いったんは残して返す。まとまり G のレース内順位を、そのレースの全出走馬から計算するため
    である（設計書 08 の 3）。人気馬だけに絞るのは、特徴量を作ったあとの ``keep_samples()`` になる。
    """

    def __init__(self, rule: FavoriteRule) -> None:
        self._rule = rule
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。``train_first_day`` より前（ウォームアップ期間）の行は、
        過去走の計算にだけ使うので入れない（設計書 08 の 3）。人気は確定単勝人気を使う。
        """
        runners = self._flat_runners.apply(entries)
        started = runners[runners["race_date"] >= pd.Timestamp(train_first_day)]
        return self._with_favorite_flag(started)

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。

        人気が1頭も分からなければ ``ValueError``、人気馬が1頭もいなければ ``LookupError``。
        """
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        if runners["popularity"].isna().all():
            raise ValueError(
                f"人気が分かりません。--pops 馬番:人気 で渡してください: {race_id}")
        return self._checked_favorites(self._with_favorite_flag(runners), race_id)

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。人気馬の行だけ（設計書 06 の図1 の5つ目の問い）。"""
        return rows[rows[IS_FAVORITE]]

    def _with_favorite_flag(self, runners: pd.DataFrame) -> pd.DataFrame:
        """「人気馬か」と「人気帯」の列を足す。頭数は、そのレースで出走した馬の数（設計書 11 の 6）。

        人気帯は人気馬の行だけに入れ、ほかの行は None にする。
        """
        field_size = runners.groupby("race_id")["horse_id"].transform("size")
        is_favorite = self._rule.are_favorites(runners["popularity"], field_size)
        band = FavoriteBand.labels_of(runners["popularity"]).where(is_favorite)
        return runners.assign(**{IS_FAVORITE: is_favorite, FAVORITE_BAND: band})

    def _checked_favorites(self, runners: pd.DataFrame, race_id: str) -> pd.DataFrame:
        if runners[IS_FAVORITE].any():
            return runners
        first, last = self._rule.popularity_range(len(runners))
        raise LookupError(
            f"人気馬がいません（{len(runners)}頭立てなので {first}〜{last}番人気が対象）: {race_id}")
