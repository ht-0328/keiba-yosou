"""利用者が ``--odds`` で渡した「馬番 → 単勝オッズ」を表す値。"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

#: 「馬番:オッズ」の区切りと、1つの引数に複数の組を書くときの区切り。
_FIELD_SEPARATOR = ":"
_PAIR_SEPARATOR = ","
#: 馬番とオッズの数。
_FIELD_COUNT = 2
#: 単勝オッズのいちばん小さい値（元返し）。これより小さい値は書き間違い。
_MIN_ODDS = 1.0


@dataclass(frozen=True)
class OddsInput:
    """``--odds 3:2.4 7:5.1`` や ``--odds 3:2.4,7:5.1`` から作る「馬番 → 単勝オッズ（倍）」（設計書 07）。

    オッズは、レースの前には確定しない。利用者が JRA の発表や投票サイトで見た単勝オッズを、そのまま渡してもらう。
    """

    pairs: tuple[tuple[int, float], ...]

    @classmethod
    def of(cls, texts: Sequence[str]) -> OddsInput:
        """引数の文字列から作る。書き方が違えば ``ValueError``（どこが悪いかを日本語で）。"""
        pairs = [cls._pair_of(text) for text in cls._split(texts)]
        cls._check_no_duplicates(pairs)
        return cls(tuple(pairs))

    def as_mapping(self) -> dict[int, float]:
        """馬番 → 単勝オッズ。"""
        return dict(self.pairs)

    @classmethod
    def _split(cls, texts: Sequence[str]) -> list[str]:
        """引数を「馬番:オッズ」1つずつに分ける。コンマ区切りも、引数を並べる書き方も受け取る。"""
        parts = [part.strip() for text in texts for part in text.split(_PAIR_SEPARATOR)]
        written = [part for part in parts if part]
        if not written:
            raise ValueError("--odds には 馬番:オッズ を1つ以上渡してください（例: --odds 3:2.4 7:5.1）")
        return written

    @classmethod
    def _pair_of(cls, text: str) -> tuple[int, float]:
        fields = text.split(_FIELD_SEPARATOR)
        if len(fields) != _FIELD_COUNT:
            raise ValueError(f"--odds は 馬番:オッズ の形で渡してください: {text!r}")
        return cls._horse_no_of(fields[0], text), cls._odds_of(fields[1], text)

    @classmethod
    def _horse_no_of(cls, field: str, text: str) -> int:
        value = field.strip()
        if not value.isdigit() or int(value) < 1:
            raise ValueError(f"馬番は 1 以上の整数で渡してください: {text!r}")
        return int(value)

    @classmethod
    def _odds_of(cls, field: str, text: str) -> float:
        try:
            odds = float(field.strip())
        except ValueError:
            raise ValueError(f"オッズは {_MIN_ODDS} 以上の数で渡してください: {text!r}") from None
        if not (math.isfinite(odds) and odds >= _MIN_ODDS):
            raise ValueError(f"オッズは {_MIN_ODDS} 以上の数で渡してください: {text!r}")
        return odds

    @classmethod
    def _check_no_duplicates(cls, pairs: Sequence[tuple[int, float]]) -> None:
        seen: set[int] = set()
        for horse_no, _ in pairs:
            if horse_no in seen:
                raise ValueError(f"同じ馬番 {horse_no} が2回出ています")
            seen.add(horse_no)
