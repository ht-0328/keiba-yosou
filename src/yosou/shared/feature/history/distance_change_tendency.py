"""距離の変更の傾向（まとまり R）: 同じコース・同じ重賞で、自分と同じ距離の変更（短縮・同じ・延長）だった馬の市場に対する成績。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.distance_change import LONGSHOT_MIN_POPULARITY

from ..odds import TOP3_RATE, WIN_RATE, MarketPlaces
from .cumulative_excess import CumulativeExcess

#: 件数の少ない組の値を 0 に寄せる強さ（この出走数ぶん、超過 0 の出走を足したとみなす）。コースは出走が多いので強めにする。
SHRINK_COURSE = 200.0
SHRINK_STAKES = 30.0
#: 特徴量の名前（並びは設計書 09 の R と同じ）。
DISTANCE_GAP = "前走との距離の差"
COURSE_STARTS = "コースの同じ距離の変更の出走数"
COURSE_WIN_EXCESS = "コースの同じ距離の変更の市場に対する超過勝率"
COURSE_TOP3_EXCESS = "コースの同じ距離の変更の市場に対する超過3着以内率"
COURSE_LONGSHOT_EXCESS = "コースの同じ距離の変更の穴馬の市場に対する超過3着以内率"
STAKES_STARTS = "重賞の同じ距離の変更の出走数"
STAKES_TOP3_EXCESS = "重賞の同じ距離の変更の市場に対する超過3着以内率"
DISTANCE_CHANGE_NAMES: tuple[str, ...] = (
    DISTANCE_GAP, COURSE_STARTS, COURSE_WIN_EXCESS, COURSE_TOP3_EXCESS, COURSE_LONGSHOT_EXCESS, STAKES_STARTS, STAKES_TOP3_EXCESS,
)
#: 突き合わせの鍵の列（一時的に足す）。
_COURSE_KEY, _STAKES_KEY = "_course_key", "_stakes_key"


class DistanceChangeTendency:
    """対象の出走ごとに、距離の変更の傾向の 7列（``DISTANCE_CHANGE_NAMES``）を作る。

    - 前走との距離の差: 今回の距離 − 前走の距離（m）。前走が無ければ欠損値。
    - コース: 同じ競馬場・コース（芝ダと内外回りを含む）・距離で、自分と同じ距離の変更だった馬の、開催日の前日までの全期間の
      出走数と、市場に対する超過勝率・超過3着以内率（(当たりの数 − オッズから見た率の和) ÷ (出走数 + 200)）。
      穴馬（6番人気以下）だけで数えた超過3着以内率も出す。
    - 重賞: 同じ重賞（特別競走番号）の過去の開催で、自分と同じ距離の変更だった馬の出走数と超過3着以内率（縮める強さ 30）。
      重賞でないレースは欠損値。

    人気の偏り（延長の馬は人気薄が多い など）を除くため、実際の率ではなく、オッズから見た率との差で数える
    （基礎統計のページの「人気から見た差」と同じ考え。騎手などの市場に対する成績 L と同じ数え方）。
    過去の出走は確定オッズから期待を出す（過去のレースの値なので、リークにならない）。オッズの無い出走は期待 0 で数える。
    """

    def of(self, targets: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
        """``targets`` は対象の出走（``race_date``（日付型）・``venue``・``course``・``distance_m``・``distance_change``・
        ``prev_distance_m``・``stakes_no``）。``runs`` は過去の平地の全出走（``race_id``・``race_date``・同じコースの列・
        ``distance_change``・``popularity``・``win_odds``・``finish``・``stakes_no``）。行の並びと index は ``targets`` と同じ。"""
        scored = self._scored(runs)
        targets = targets.assign(**{_COURSE_KEY: _course_key(targets), _STAKES_KEY: _stakes_key(targets)})
        course = CumulativeExcess(targets, _COURSE_KEY)
        stakes = CumulativeExcess(targets, _STAKES_KEY)
        longshots = scored[pd.to_numeric(scored["popularity"], errors="coerce") >= LONGSHOT_MIN_POPULARITY]
        course_win = course.totals(scored, "won", "expected_win")
        course_top3 = course.totals(scored, "placed", "expected_top3")
        course_longshot = course.totals(longshots, "placed", "expected_top3")
        stakes_top3 = stakes.totals(scored[scored[_STAKES_KEY].notna()], "placed", "expected_top3")
        is_stakes = targets["stakes_no"].notna()
        return pd.DataFrame({
            DISTANCE_GAP: pd.to_numeric(targets["distance_m"], errors="coerce") - pd.to_numeric(targets["prev_distance_m"], errors="coerce"),
            COURSE_STARTS: course_top3["starts"],
            COURSE_WIN_EXCESS: _excess(course_win, SHRINK_COURSE),
            COURSE_TOP3_EXCESS: _excess(course_top3, SHRINK_COURSE),
            COURSE_LONGSHOT_EXCESS: _excess(course_longshot, SHRINK_COURSE),
            STAKES_STARTS: stakes_top3["starts"].where(is_stakes),
            STAKES_TOP3_EXCESS: _excess(stakes_top3, SHRINK_STAKES).where(is_stakes),
        }, index=targets.index).astype("float64")

    @staticmethod
    def _scored(runs: pd.DataFrame) -> pd.DataFrame:
        """過去の出走に、1着か（``won``）・3着以内か（``placed``）・オッズから見た勝率と3着以内率・突き合わせの鍵を足す。"""
        market = MarketPlaces().of(runs[["race_id", "win_odds"]])
        finish = pd.to_numeric(runs["finish"], errors="coerce")
        return runs.assign(
            won=finish.eq(1).astype(float), placed=finish.between(1, 3).astype(float),
            expected_win=market[WIN_RATE].fillna(0.0).to_numpy(), expected_top3=market[TOP3_RATE].fillna(0.0).to_numpy(),
            **{_COURSE_KEY: _course_key(runs), _STAKES_KEY: _stakes_key(runs)},
        )


def _course_key(frame: pd.DataFrame) -> pd.Series:
    """競馬場・コース・距離・距離の変更をつないだ鍵。どれかが無ければ欠損値。"""
    distance = pd.to_numeric(frame["distance_m"], errors="coerce").astype("Int64").astype("string")
    key = frame["venue"].astype("string") + "|" + frame["course"].astype("string") + "|" + distance + "|" \
        + frame["distance_change"].astype("string")
    return key.astype(object).where(key.notna(), np.nan)


def _stakes_key(frame: pd.DataFrame) -> pd.Series:
    """特別競走番号と距離の変更をつないだ鍵。重賞でなければ欠損値。"""
    key = frame["stakes_no"].astype("string") + "|" + frame["distance_change"].astype("string")
    return key.astype(object).where(key.notna(), np.nan)


def _excess(totals: pd.DataFrame, shrink: float) -> pd.Series:
    """(当たりの数 − 期待の和) ÷ (出走数 + 縮める強さ)。"""
    return (totals["hits"] - totals["expected"]) / (totals["starts"] + shrink)
