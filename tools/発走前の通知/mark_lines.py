"""通知の文に書く印の行（1つの印につき1行。◎○▲△☆注消の順、無印は書かない）。中央と地方で同じ形にする。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, MARK_REASON
from 今週の予想.mark_rule import MARK_ORDER, NO_MARK, NOTE_MARK, OUT_MARK, TOP_MARK, VALUE_MARK

#: 同じ印の馬をつなぐ字。
_JOIN = "・"
#: 理由を添える印（1頭だけに付き、選び方が印ごとに違うもの）。○▲△ は3着以内の確率の順なので添えない。
_EXPLAINED: tuple[str, ...] = (TOP_MARK, VALUE_MARK, NOTE_MARK, OUT_MARK)


class MarkLines:
    """例 ``◎ 9 アグレイビューティ：単勝 30倍以下の馬の中で単勝の期待値がレース内1位（…）``・``△ 13 トラカイキャッスル・4 アトレッタ``。
    同じ印の中は表の並び（3着以内の確率の高い順）。◎・☆・注・消 の行には、その馬にその印が付いた理由（``MarkRule`` が書いた
    ``mark_reason``）を「：」のあとに添える。馬番が無い（枠順がまだ無い木曜の予想）馬は「-」。"""

    def lines(self, table: pd.DataFrame) -> list[str]:
        lines = []
        for mark in MARK_ORDER:
            if mark == NO_MARK:
                continue
            horses = table[table[MARK] == mark]
            if horses.empty:
                continue
            line = f"{mark} " + _JOIN.join(self._horse(row) for _, row in horses.iterrows())
            reason = self._reason(horses) if mark in _EXPLAINED else ""
            lines.append(f"{line}：{reason}" if reason else line)
        return lines

    @staticmethod
    def _horse(row: pd.Series) -> str:
        number = int(row[HORSE_NO]) if pd.notna(row[HORSE_NO]) else "-"
        return f"{number} {row[HORSE_NAME]}"

    @staticmethod
    def _reason(horses: pd.DataFrame) -> str:
        if MARK_REASON not in horses.columns or len(horses) != 1:
            return ""
        reason = horses[MARK_REASON].iloc[0]
        return str(reason) if isinstance(reason, str) else ""
