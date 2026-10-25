"""半年ごとの区切り（道具「印の成績」と同じ名前）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Fold:
    """1つの区切り。``first_day`` 以上 ``next_first_day`` 未満の開催日がこの区切り。``valid_first_day`` は、その区切りを予測するモデルの検証データの始まり
    （直前の半年）。学習データは、学習の始まりから検証データの始まりの前日まで。"""

    name: str
    first_day: date
    next_first_day: date
    valid_first_day: date


def half_year_folds(first_year: int = 2015, last_year: int = 2026) -> list[Fold]:
    """``first_year`` の前半から ``last_year`` までの半年の区切り。最後の年は1年を1つの区切りにする（印を付けた表の ``2026年`` と同じ名前）。

    例: 2015年前半 = 2015-01-01〜06-30（検証は 2014-07-01〜12-31）、2026年 = 2026-01-01〜12-31。
    """
    folds: list[Fold] = []
    for year in range(first_year, last_year):
        folds.append(Fold(f"{year}年前半", date(year, 1, 1), date(year, 7, 1), date(year - 1, 7, 1)))
        folds.append(Fold(f"{year}年後半", date(year, 7, 1), date(year + 1, 1, 1), date(year, 1, 1)))
    folds.append(Fold(f"{last_year}年", date(last_year, 1, 1), date(last_year + 1, 1, 1), date(last_year - 1, 7, 1)))
    return folds
