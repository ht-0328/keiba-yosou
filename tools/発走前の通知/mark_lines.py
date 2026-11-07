"""通知の文に書く印の行（1つの印につき1行。◎○▲△☆注消の順、無印は書かない）。中央と地方で同じ形にする。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK
from 今週の予想.mark_rule import MARK_ORDER, NO_MARK

#: 同じ印の馬をつなぐ字。
_JOIN = "・"


class MarkLines:
    """例 ``◎ 9 アグレイビューティ``・``△ 13 トラカイキャッスル・4 アトレッタ``。同じ印の中は表の並び（3着以内の確率の高い順）。
    馬番が無い（枠順がまだ無い木曜の予想）馬は「-」。"""

    def lines(self, table: pd.DataFrame) -> list[str]:
        lines = []
        for mark in MARK_ORDER:
            if mark == NO_MARK:
                continue
            horses = table[table[MARK] == mark]
            if not horses.empty:
                lines.append(f"{mark} " + _JOIN.join(self._horse(row) for _, row in horses.iterrows()))
        return lines

    @staticmethod
    def _horse(row: pd.Series) -> str:
        number = int(row[HORSE_NO]) if pd.notna(row[HORSE_NO]) else "-"
        return f"{number} {row[HORSE_NAME]}"
