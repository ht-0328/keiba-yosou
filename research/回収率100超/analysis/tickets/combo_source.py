"""買い目の確率の出どころの決まり（インターフェース）。"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .ticket_kind import TicketKind


class ComboSource(Protocol):
    """レースごとに、券種の全部の買い目の確率の表を返すもの。

    表の番号は ``TicketKind.flat_index`` と同じ。そのレースの確率が作れなければ None を返す。
    例: ``WinBasedSource``（モデルの1着の確率から Harville の式で作る）。
    """

    def table(self, kind: TicketKind, rid: int) -> np.ndarray | None: ...
