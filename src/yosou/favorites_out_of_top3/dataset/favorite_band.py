"""人気馬の人気帯（1番人気・2〜3番人気・4〜5番人気）を表す値。"""

from __future__ import annotations

from enum import Enum

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers


class FavoriteBand(Enum):
    """人気馬の人気帯（既存モデルの修正計画の 1「人気馬の4着以下」）。帯ごとに別のモデルで学ぶ。

    1番人気より4・5番人気のほうが普通に負けやすいので、まとめて学ぶと「人気が低い馬」を危険としやすい。
    帯に分けると、それぞれの帯の中で「普段より危ない馬」を見分ける形になる。
    値は人が読む名前で、評価用の列・出力の表の値にそのまま使う。4〜5番人気は 14頭以上のレースにだけある。
    """

    FIRST = "1番人気"
    SECOND_THIRD = "2〜3番人気"
    FOURTH_FIFTH = "4〜5番人気"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return self.value

    @property
    def key(self) -> str:
        """モデルを置くフォルダの名前（first・second_third・fourth_fifth）。"""
        return _KEYS[self]

    @classmethod
    def labels_of(cls, popularity: pd.Series) -> pd.Series:
        """人気順位の列から、人気帯の名前の列。1〜5番人気でなければ None。"""
        ranks = as_numbers(popularity)
        labels = np.select(
            [ranks == 1, ranks.between(2, 3), ranks.between(4, 5)],
            [cls.FIRST.label, cls.SECOND_THIRD.label, cls.FOURTH_FIFTH.label], default=None,
        )
        return pd.Series(labels, index=popularity.index, dtype=object)


_KEYS: dict[FavoriteBand, str] = {
    FavoriteBand.FIRST: "first", FavoriteBand.SECOND_THIRD: "second_third", FavoriteBand.FOURTH_FIFTH: "fourth_fifth",
}
