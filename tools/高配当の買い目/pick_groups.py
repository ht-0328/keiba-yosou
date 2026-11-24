"""買い目を、券種ごとと合計に分ける。"""

from __future__ import annotations

import pandas as pd

from 高配当の買い目.pick_columns import TICKET_TYPE, TOTAL


class PickGroups:
    """買い目の表（1行 = 1点。列 ``ticket_type`` は券種の名前）を、表の行にする組（券種ごと。最後に全部を合わせた ``合計``）に分ける。

    ``labels`` は券種の名前の並び（表に出す順）。買った点の無い券種も、空の表で返す（表に 0 の行を出すため）。
    例: ``PickGroups(("ワイド", "馬連")).of(picks)`` → ``[("ワイド", …), ("馬連", …), ("合計", picks)]``。
    """

    def __init__(self, labels: tuple[str, ...]) -> None:
        self._labels = labels

    def of(self, picks: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
        by_ticket = [(label, picks[picks[TICKET_TYPE] == label]) for label in self._labels]
        return [*by_ticket, (TOTAL, picks)]
