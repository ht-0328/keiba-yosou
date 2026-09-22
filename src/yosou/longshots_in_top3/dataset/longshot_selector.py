"""学習データ・予測用データに入れる行を選び、「穴馬か」「穴馬の区分」を足す。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter

from .column_names import IS_LONGSHOT, LONGSHOT_ZONE
from .longshot_rule import LongshotRule


class LongshotSelector:
    """入れる行を選ぶ（設計書 06 の図1・図2）。``SampleSelector`` を守る。

    穴馬でない行も、いったんは残して返す。まとまり G のレース内順位を、そのレースの全出走馬から計算するため
    である（設計書 08 の 3）。穴馬だけに絞るのは、特徴量を作ったあとの ``keep_samples()`` になる。
    「穴馬の区分」の列は、出力の表と評価に使うもので、モデルには渡さない（設計書 08 の 2）。
    """

    def __init__(self, rule: LongshotRule) -> None:
        self._rule = rule
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。``train_first_day`` より前（ウォームアップ期間）の行は、
        過去走の計算にだけ使うので入れない（設計書 08 の 3）。人気は確定単勝人気を使う。
        """
        runners = self._flat_runners.apply(entries)
        started = runners[runners["race_date"] >= pd.Timestamp(train_first_day)]
        return self._with_longshot_columns(started)

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。

        人気の分からない馬が1頭でもいれば ``ValueError``（穴馬は出走馬の大半なので、黙って落とさない。
        設計書 06 の図2）。穴馬が1頭もいなければ ``LookupError``。
        """
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        self._check_popularity_known(runners, race_id)
        return self._checked_longshots(self._with_longshot_columns(runners), race_id)

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。穴馬の行だけ（設計書 06 の図1 の6つ目の問い）。"""
        return rows[rows[IS_LONGSHOT]]

    def _with_longshot_columns(self, runners: pd.DataFrame) -> pd.DataFrame:
        """「穴馬か」「穴馬の区分」の列を足す。頭数は、そのレースで出走した馬の数（設計書 11 の 6）。"""
        field_size = runners.groupby("race_id")["horse_id"].transform("size")
        return runners.assign(**{
            IS_LONGSHOT: self._rule.are_longshots(runners["popularity"], field_size),
            LONGSHOT_ZONE: self._rule.zones_of(runners["popularity"], field_size),
        })

    def _check_popularity_known(self, runners: pd.DataFrame, race_id: str) -> None:
        """全頭の人気がそろっているか。1頭でも分からなければ止める（設計書 07）。"""
        unknown = int(runners["popularity"].isna().sum())
        if unknown == len(runners):
            raise ValueError(
                f"人気が分かりません。--pops で全頭の人気（馬番:人気。木曜は 馬名:人気）を渡してください: {race_id}")
        if unknown:
            raise ValueError(
                f"人気の分からない馬が {unknown}頭います（{len(runners)}頭立て）。"
                f"--pops で全頭の人気を渡してください: {race_id}")

    def _checked_longshots(self, runners: pd.DataFrame, race_id: str) -> pd.DataFrame:
        if runners[IS_LONGSHOT].any():
            return runners
        first, last = self._rule.popularity_range(len(runners))
        raise LookupError(
            f"穴馬がいません（{len(runners)}頭立てなので {first}〜{last}番人気が対象）: {race_id}")
