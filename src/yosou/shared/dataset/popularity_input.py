"""利用者が ``--pops`` で渡した「馬番（か馬名）→ 人気」を表す値。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

#: 「馬番:人気」の区切りと、1つの引数に複数の組を書くときの区切り。
_FIELD_SEPARATOR = ":"
_PAIR_SEPARATOR = ","
#: 馬の指定と人気の数。
_FIELD_COUNT = 2
#: 誤りの文面に使う、書き方の案内。
_FORMAT = "馬番:人気（木曜は 馬名:人気）"


@dataclass(frozen=True)
class PopularityInput:
    """``--pops 3:1 7:2`` や ``--pops 3:1,7:2`` から作る「馬番 → 人気」（人気馬・穴馬の設計書 07）。

    人気は、レースの前には確定しない。利用者が JRA の発表や投票サイトで見た人気を、そのまま渡してもらう。
    馬番がまだ決まっていない木曜（出走馬名表）は、馬番の代わりに馬名で渡す（``--pops ウマ001:1``）。
    馬の指定が数字だけなら馬番、そうでなければ馬名とみなす。
    """

    pairs: tuple[tuple[int | str, int], ...]

    @classmethod
    def of(cls, texts: Sequence[str]) -> PopularityInput:
        """引数の文字列から作る。書き方が違えば ``ValueError``（どこが悪いかを日本語で）。"""
        pairs = [cls._pair_of(text) for text in cls._split(texts)]
        cls._check_no_duplicates(pairs)
        return cls(tuple(pairs))

    def as_mapping(self) -> dict[int | str, int]:
        """馬番（か馬名）→ 人気。"""
        return dict(self.pairs)

    @classmethod
    def _split(cls, texts: Sequence[str]) -> list[str]:
        """引数を「馬番:人気」1つずつに分ける。コンマ区切りも、引数を並べる書き方も受け取る。"""
        parts = [part.strip() for text in texts for part in text.split(_PAIR_SEPARATOR)]
        written = [part for part in parts if part]
        if not written:
            raise ValueError(f"--pops には {_FORMAT} を1つ以上渡してください（例: --pops 3:1 7:2）")
        return written

    @classmethod
    def _pair_of(cls, text: str) -> tuple[int | str, int]:
        fields = text.split(_FIELD_SEPARATOR)
        if len(fields) != _FIELD_COUNT:
            raise ValueError(f"--pops は {_FORMAT} の形で渡してください: {text!r}")
        return cls._horse_of(fields[0], text), cls._number_of(fields[1], "人気", text)

    @classmethod
    def _horse_of(cls, field: str, text: str) -> int | str:
        """馬の指定。数字だけなら馬番（1 以上）、そうでなければ馬名。"""
        value = field.strip()
        if value.isdigit():
            return cls._number_of(value, "馬番", text)
        if not value:
            raise ValueError(f"馬番か馬名を渡してください: {text!r}")
        return value

    @classmethod
    def _number_of(cls, field: str, name: str, text: str) -> int:
        value = field.strip()
        if not value.isdigit() or int(value) < 1:
            raise ValueError(f"{name}は 1 以上の整数で渡してください: {text!r}")
        return int(value)

    @classmethod
    def _check_no_duplicates(cls, pairs: Sequence[tuple[int | str, int]]) -> None:
        """同じ馬（馬番か馬名）と同じ人気が2回出ていないか。"""
        seen_horses: set[int | str] = set()
        seen_ranks: set[int] = set()
        for horse, rank in pairs:
            if horse in seen_horses:
                raise ValueError(f"同じ{_kind_of(horse)} {horse} が2回出ています")
            if rank in seen_ranks:
                raise ValueError(f"同じ人気 {rank} が2回出ています")
            seen_horses.add(horse)
            seen_ranks.add(rank)


def _kind_of(horse: int | str) -> str:
    """誤りの文面に使う、馬の指定の呼び方。"""
    return "馬番" if isinstance(horse, int) else "馬名"
