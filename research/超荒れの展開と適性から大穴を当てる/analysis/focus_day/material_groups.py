"""理由の文で使う、特徴量のまとまり（展開・馬場・ハンデ・近走と力）。"""

from __future__ import annotations

from dataclasses import dataclass

#: まとまりの名前。
DEVELOPMENT, TRACK, HANDICAP, FORM = "展開", "馬場", "ハンデ", "近走と力"
_DEVELOPMENT_WORDS = ("展開", "予想_", "位置", "脚質", "ペース", "4角", "4コーナー", "序盤", "逃げ", "先行")
_TRACK_WORDS = ("傾き", "馬番", "枠")
_HANDICAP_WORDS = ("斤量", "ハンデ", "トップとの差", "昇級")


@dataclass(frozen=True)
class MaterialGroups:
    """列名から、まとまりを決める。ハンデ → 馬場 → 展開 の順に言葉で見分け、どれでもなければ近走と力。"""

    def of(self, column: str) -> str:
        if any(word in column for word in _HANDICAP_WORDS):
            return HANDICAP
        if any(word in column for word in _TRACK_WORDS):
            return TRACK
        if any(word in column for word in _DEVELOPMENT_WORDS):
            return DEVELOPMENT
        return FORM
