"""比べる相手 (1): ルール集の WIN5 のルールの買い目。"""

from __future__ import annotations

from collections.abc import Sequence

from ..formation import Formation

#: 上位人気（1・2番人気）と、穴馬（4〜6番人気）の、人気の順の位置。
_FAVORITES = slice(0, 2)
_LONGSHOTS = slice(3, 6)


class RuleFormations:
    """ルール集の WIN-02（``docs/rules/馬券の買い方/10-win5.md``）: 1レースだけ穴馬3頭（4〜6番人気）・残り4レースは上位人気2頭
    （1・2番人気）の 48点を、穴馬を入れるレースを1つずつずらして5セット、計 240点（設計書 16 の 5.）。人気はオッズの順。"""

    def of(self, popularity: Sequence[Sequence[int]]) -> tuple[Formation, ...]:
        """``popularity`` は5レースの、人気の順に並べた馬番。5つのフォーメーション（セット）を返す。"""
        return tuple(self._set(popularity, longshot_leg) for longshot_leg in range(len(popularity)))

    def _set(self, popularity: Sequence[Sequence[int]], longshot_leg: int) -> Formation:
        return Formation(tuple(
            tuple(numbers[_LONGSHOTS] if leg == longshot_leg else numbers[_FAVORITES])
            for leg, numbers in enumerate(popularity)
        ))
