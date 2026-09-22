"""予測する時点（木曜・前日・当日。設計書 07-prediction-timing.md）。"""

from __future__ import annotations

from enum import Enum


class PredictionTiming(Enum):
    """予測する時点。値は、モデルを保存するフォルダの名前にも使う。並びは時間の順（木曜 → 前日 → 当日）。

    その時点でどの特徴量が分かるかは、特徴量の側（``Feature.known_from``）に書き、
    ``FeatureCatalog.columns_for`` が答える。
    """

    THURSDAY = "thursday"
    DAY_BEFORE = "day_before"
    RACE_DAY = "race_day"

    @property
    def label(self) -> str:
        """人が読む名前（木曜・前日・当日）。"""
        return _LABELS[self]

    def is_at_or_after(self, other: PredictionTiming) -> bool:
        """この時点が ``other`` と同じか、それより後か。後の時点ほど、分かることが多い。"""
        return _ORDER.index(self) >= _ORDER.index(other)

    @classmethod
    def parse(cls, text: str) -> PredictionTiming:
        """``木曜`` か ``thursday`` のような書き方から時点を返す。知らなければ ``ValueError``。"""
        timing = _TIMING_BY_TEXT.get(text.strip())
        if timing is None:
            names = " / ".join(f"{each.label}（{each.value}）" for each in cls)
            raise ValueError(f"知らない時点です: {text}（{names}）")
        return timing


#: 時間の順。
_ORDER: list[PredictionTiming] = list(PredictionTiming)
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
