"""正解を作らなかったレースの数と割合を、条件ごとに数える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..dataset import label_names as names
from ..feature.history.pace_baseline import NO_BASELINE

#: 入力の列（1行 = 1レース。``BacktestFrames.unlabeled`` が作る）。
YEAR, VENUE, FIELD_SIZE, PACE_NAME = "年", "競馬場", "頭数", "ペースの区分の名前"
#: 基準の段の列（``names`` の前半・後半タイムの基準に付ける）。
FIRST_STAGE, SECOND_STAGE = "前半タイムの基準の段", "後半タイムの基準の段"
#: 直線コースのトラックコード（芝・直線、ダート・直線）。
STRAIGHT_TRACKS = frozenset({"10", "29"})
#: 頭数の帯（設計書 16 の 2 と同じ）。
FIELD_BANDS: tuple[tuple[str, int, int], ...] = (("〜10頭", 0, 10), ("11〜14頭", 11, 14), ("15頭〜", 15, 99))
#: 理由の並び（①② の先頭と位置、③ の前半、⑥ の後半）。
LEADER_REASONS: tuple[str, ...] = ("直線", "コーナーを5回以上通る", "通過順位の記録なし", "先頭が決まらない")
HALF_REASONS: tuple[str, ...] = ("タイムの記録なし", "基準なし")
#: 出力の列。
ASPECT, VALUE, RACES = "切り口", "値", "レース数"
#: 先頭が決まらないレースの例を、いくつまで出すか（設計書 16 の 4 の「20 レースを抜き出し」）。
EXAMPLE_COUNT = 20


class UnlabeledRaceTable:
    """正解を作らなかったレースを、理由ごとに、頭数・競馬場・ペースの区分・年の切り口で数える（設計書 16 の 4）。

    正解を作れるレースだけで学習・評価すると、作れるレースだけで当たりが良く見えることがあるので、作らなかったレースが
    特定の条件に偏っていないかを見る。理由は、①② の先頭と位置（直線・コーナーを5回以上通る・通過順位の記録なし・
    先頭が決まらない）と、③⑥ の前半・後半タイム（タイムの記録なし・基準なし）。1つのレースには、上の順で最初に
    当てはまった理由を1つだけ付ける。
    """

    def table(self, races: pd.DataFrame) -> pd.DataFrame:
        """切り口ごとの行（``切り口``・``値``・``レース数`` と、理由ごとの割合）。割合は 0〜1。"""
        reasons = self._reasons(races)
        framed = pd.concat([races[[YEAR, VENUE]], reasons], axis=1).assign(**{
            "_頭数": self._field_band(races[FIELD_SIZE]), "_ペース": races[PACE_NAME].fillna("区分なし"), "_全体": "全部",
        })
        aspects = (("全体", "_全体"), ("頭数", "_頭数"), ("競馬場", VENUE), ("ペースの区分", "_ペース"), ("年", YEAR))
        return pd.concat([self._counted(framed, label, column) for label, column in aspects], ignore_index=True)

    def examples(self, races: pd.DataFrame) -> list[str]:
        """先頭が決まらないレースの、レースID（新しい順に最大 ``EXAMPLE_COUNT``）。通過順と照らし合わせるための一覧。"""
        reasons = self._reasons(races)
        undecided = races.loc[reasons["①② の理由"] == LEADER_REASONS[3], "race_id"]
        return [str(race_id) for race_id in undecided.iloc[::-1].head(EXAMPLE_COUNT)]

    def _reasons(self, races: pd.DataFrame) -> pd.DataFrame:
        """レースごとの理由（①② と ③ と ⑥。正解を作れたレースは空の文字列）。"""
        track = races[names.TRACK_CODE].astype("string").str.strip()
        corner = pd.to_numeric(races[names.FIRST_CORNER_NO], errors="coerce")
        leader = pd.to_numeric(races[names.FIRST_CORNER_LEADER_NO], errors="coerce")
        laps = races[names.CORNER_LAPS_OVER_ONE].fillna(False).astype(bool)
        leader_reason = np.select(
            [track.isin(STRAIGHT_TRACKS).to_numpy(), laps.to_numpy(), corner.isna().to_numpy(), leader.isna().to_numpy()],
            list(LEADER_REASONS), default="",
        )
        return pd.DataFrame({
            "①② の理由": leader_reason,
            "③ の理由": self._half_reason(races[names.FIRST_HALF_TIME], races[FIRST_STAGE]),
            "⑥ の理由": self._half_reason(races[names.SECOND_HALF_TIME], races[SECOND_STAGE]),
        }, index=races.index)

    def _half_reason(self, time: pd.Series, stage: pd.Series) -> np.ndarray:
        missing = pd.to_numeric(time, errors="coerce").isna().to_numpy()
        no_baseline = (stage.astype("string") == NO_BASELINE).fillna(True).to_numpy()
        return np.select([missing, no_baseline], list(HALF_REASONS), default="")

    def _field_band(self, field_size: pd.Series) -> pd.Series:
        size = pd.to_numeric(field_size, errors="coerce")
        bands = [(size >= low) & (size <= high) for _, low, high in FIELD_BANDS]
        return pd.Series(np.select(bands, [label for label, _, _ in FIELD_BANDS], default="不明"), index=field_size.index)

    def _counted(self, framed: pd.DataFrame, label: str, column: str) -> pd.DataFrame:
        """1つの切り口の、値ごとのレース数と、理由ごとの割合。"""
        shares = {
            f"{stage} {reason}": (framed[f"{stage} の理由"] == reason).groupby(framed[column]).mean()
            for stage, reasons in (("①②", LEADER_REASONS), ("③", HALF_REASONS), ("⑥", HALF_REASONS)) for reason in reasons
        }
        counted = pd.DataFrame({RACES: framed.groupby(column).size(), **shares})
        return counted.rename_axis(VALUE).reset_index().assign(**{ASPECT: label})[[ASPECT, VALUE, RACES, *shares]]
