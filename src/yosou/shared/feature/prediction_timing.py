"""予測する時点（木曜・前日・当日）と、時点ごとに使う特徴量（設計書 07-prediction-timing.md）。"""

from __future__ import annotations

from enum import Enum


class PredictionTiming(Enum):
    """予測する時点。値は、モデルを保存するフォルダの名前にも使う。"""

    THURSDAY = "thursday"
    DAY_BEFORE = "day_before"
    RACE_DAY = "race_day"

    @property
    def label(self) -> str:
        """人が読む名前（木曜・前日・当日）。"""
        return _LABELS[self]

    @property
    def unknown_features(self) -> frozenset[str]:
        """この時点ではまだ分からない特徴量の名前。使う列を決めるのは ``FeatureCatalog.columns_for``。"""
        return _UNKNOWN_FEATURES[self]

    @classmethod
    def parse(cls, text: str) -> PredictionTiming:
        """``木曜`` か ``thursday`` のような書き方から時点を返す。知らなければ ``ValueError``。"""
        timing = _TIMING_BY_TEXT.get(text.strip())
        if timing is None:
            names = " / ".join(f"{each.label}（{each.value}）" for each in cls)
            raise ValueError(f"知らない時点です: {text}（{names}）")
        return timing


_LABELS: dict[PredictionTiming, str] = {
    PredictionTiming.THURSDAY: "木曜",
    PredictionTiming.DAY_BEFORE: "前日",
    PredictionTiming.RACE_DAY: "当日",
}
#: 時点の書き方（日本語の名前と、英語の値）→ 時点。
_TIMING_BY_TEXT: dict[str, PredictionTiming] = {
    **{timing.label: timing for timing in PredictionTiming},
    **{timing.value: timing for timing in PredictionTiming},
}

#: 前日に分からない特徴量。馬体重の発表は当日。
_UNKNOWN_ON_DAY_BEFORE: frozenset[str] = frozenset({"馬体重", "馬体重の増減"})
#: 木曜に分からない特徴量。枠番・馬番は出馬表（金曜）、馬場状態は前日に決まる。
#: 馬場状態で分けて数える特徴量（通算の成績と持ち時計）も使わない。
_UNKNOWN_ON_THURSDAY: frozenset[str] = _UNKNOWN_ON_DAY_BEFORE | {
    "枠番", "馬番", "馬場状態",
    "同じ芝ダ・馬場状態での通算の出走数", "同じ芝ダ・馬場状態での通算の3着以内の数",
    "持ち時計のレース内順位（コース単位）", "持ち時計のレース内順位（距離単位）",
}
_UNKNOWN_FEATURES: dict[PredictionTiming, frozenset[str]] = {
    PredictionTiming.THURSDAY: _UNKNOWN_ON_THURSDAY,
    PredictionTiming.DAY_BEFORE: _UNKNOWN_ON_DAY_BEFORE,
    PredictionTiming.RACE_DAY: frozenset(),
}
