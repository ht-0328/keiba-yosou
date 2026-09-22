"""利用者が ``--pops`` で渡した「馬番 → 人気」を表す値。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

#: 「馬番:人気」の区切りと、1つの引数に複数の組を書くときの区切り。
_FIELD_SEPARATOR = ":"
_PAIR_SEPARATOR = ","
#: 馬番と人気の数。
_FIELD_COUNT = 2


@dataclass(frozen=True)
class PopularityInput:
    """``--pops 3:1 7:2`` や ``--pops 3:1,7:2`` から作る「馬番 → 人気」（設計書 07）。

    人気は、レースの前には確定しない。利用者が JRA の発表や投票サイトで見た人気を、そのまま渡してもらう。
    """

    pairs: tuple[tuple[int, int], ...]

    @classmethod
    def of(cls, texts: Sequence[str]) -> PopularityInput:
        """引数の文字列から作る。書き方が違えば ``ValueError``（どこが悪いかを日本語で）。"""
        pairs = [cls._pair_of(text) for text in cls._split(texts)]
        cls._check_no_duplicates(pairs)
        return cls(tuple(pairs))

    def as_mapping(self) -> dict[int, int]:
        """馬番 → 人気。"""
        return dict(self.pairs)

    @classmethod
    def _split(cls, texts: Sequence[str]) -> list[str]:
        """引数を「馬番:人気」1つずつに分ける。コンマ区切りも、引数を並べる書き方も受け取る。"""
        parts = [part.strip() for text in texts for part in text.split(_PAIR_SEPARATOR)]
        written = [part for part in parts if part]
        if not written:
            raise ValueError("--pops には 馬番:人気 を1つ以上渡してください（例: --pops 3:1 7:2）")
        return written

    @classmethod
    def _pair_of(cls, text: str) -> tuple[int, int]:
        fields = text.split(_FIELD_SEPARATOR)
        if len(fields) != _FIELD_COUNT:
            raise ValueError(f"--pops は 馬番:人気 の形で渡してください: {text!r}")
        return cls._number_of(fields[0], "馬番", text), cls._number_of(fields[1], "人気", text)

    @classmethod
    def _number_of(cls, field: str, name: str, text: str) -> int:
        value = field.strip()
        if not value.isdigit() or int(value) < 1:
            raise ValueError(f"{name}は 1 以上の整数で渡してください: {text!r}")
        return int(value)

    @classmethod
    def _check_no_duplicates(cls, pairs: Sequence[tuple[int, int]]) -> None:
        cls._check_unique([horse_no for horse_no, _ in pairs], "馬番")
        cls._check_unique([rank for _, rank in pairs], "人気")

    @classmethod
    def _check_unique(cls, values: Sequence[int], name: str) -> None:
        seen: set[int] = set()
        for value in values:
            if value in seen:
                raise ValueError(f"同じ{name} {value} が2回出ています")
            seen.add(value)
