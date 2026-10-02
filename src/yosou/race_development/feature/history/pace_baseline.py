"""前半タイム・後半タイムの基準を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

#: 基準を数える日数（前日までの3年。設計書 10 の 5）。
BASELINE_WINDOW_DAYS = 1095
#: 基準に要るレースの数と、標準偏差の下限（秒）。どちらも初期値（設計書 14 の「設定ファイルに書かないもの」）。
MIN_RACES = 30
MIN_STD = 0.1
#: 基準の段（設計書 06 の図2a）。
SAME_CLASS, MERGED_CLASS, NO_BASELINE = "同じクラス", "クラスをまとめた", "なし"
#: 出力の列の名前の後ろ。頭は作られるときに受け取る（「前半タイムの基準」「後半タイムの基準」）。
MEAN, STD, COUNT, STAGE = "", "の標準偏差", "の件数", "の段"
#: 前半タイムと後半タイムの基準の列の名前の頭（設計書 09 の Q・U）。
FIRST_HALF_BASELINE = "前半タイムの基準"
SECOND_HALF_BASELINE = "後半タイムの基準"
#: コースの鍵（競馬場・コース・距離）とクラスの列。
_COURSE_KEY: tuple[str, ...] = ("venue_code", "track_code", "distance_m")
_CLASS_KEY: tuple[str, ...] = (*_COURSE_KEY, "class_order")
_STATS: tuple[str, ...] = ("mean", "std", "count")


class PaceBaseline:
    """各レースに、前半（か後半）タイムの基準を付ける（設計書 06 の図2a・10 の 5.・9.）。**基準の、ただ1つの置き場所。**

    基準は、そのレースの開催日の前日までの 1095日に行われた、同じ競馬場・コース・距離・クラスのレースのタイムの平均と
    標準偏差。30 レースに満たなければクラスをまとめ、それでも満たないか、標準偏差が 0.1秒より小さければ「基準なし」。
    同じ日のレースは数えない（予測のときは、同じ日のレースの結果はまだ無いため。設計書 11 の 7・8）。
    ``time_column`` はタイムの列（``first3f`` か ``last3f_race``）、``name`` は出力の列の名前の頭。
    """

    def __init__(self, time_column: str, name: str) -> None:
        self._time_column = time_column
        self._name = name

    def column(self, suffix: str) -> str:
        """出力の列の名前（``MEAN``・``STD``・``COUNT``・``STAGE`` を後ろに付ける）。"""
        return self._name + suffix

    def attach(self, races: pd.DataFrame) -> pd.DataFrame:
        """``races`` は1行 = 1レース（列 ``race_date``・コースの鍵・``class_order``・タイムの列）。基準の4列を足して返す。
        行の並びと index は ``races`` と同じ。成績の無いレース（タイムが欠損値）も、基準は付く。
        """
        ordered = races.assign(race_date=pd.to_datetime(races["race_date"])).sort_values("race_date", kind="stable")
        by_class = self._rolled(ordered, _CLASS_KEY)
        by_course = self._rolled(ordered, _COURSE_KEY)
        use_class = (by_class["count"] >= MIN_RACES) & (by_class["std"] >= MIN_STD)
        use_course = ~use_class & (by_course["count"] >= MIN_RACES) & (by_course["std"] >= MIN_STD)
        chosen = {stat: by_class[stat].where(use_class, by_course[stat].where(use_course)) for stat in _STATS}
        attached = pd.DataFrame({
            self.column(MEAN): chosen["mean"],
            self.column(STD): chosen["std"],
            self.column(COUNT): chosen["count"],
            self.column(STAGE): np.select([use_class, use_course], [SAME_CLASS, MERGED_CLASS], default=NO_BASELINE),
        }, index=ordered.index)
        return pd.concat([races, attached.reindex(races.index)], axis=1)

    def _rolled(self, races: pd.DataFrame, keys: tuple[str, ...]) -> pd.DataFrame:
        """鍵ごとに、開催日の前日までの 1095日の平均・標準偏差・件数。``races`` は開催日の順で、戻り値も同じ index。"""
        times = as_numbers(races[self._time_column]).to_numpy()
        days = races["race_date"].to_numpy()
        values = np.full((len(races), len(_STATS)), np.nan)
        for rows in races.groupby(list(keys), sort=False).indices.values():
            window = pd.Series(times[rows], index=days[rows]).rolling(f"{BASELINE_WINDOW_DAYS}D", closed="left")
            values[rows] = np.column_stack([window.mean(), window.std(), window.count()])
        return pd.DataFrame(values, columns=list(_STATS), index=races.index)
