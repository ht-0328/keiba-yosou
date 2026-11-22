"""AI＋ロジック予想の展開のロジック: 逃げ・先行の馬が少なくペースが遅くなりそうなレースで、◎ が差し・追込なら、全レースの印の買い目を見送る。"""

from __future__ import annotations

from collections.abc import Mapping

#: 逃げ・先行の馬が頭数のこの割合以下なら、ペースが遅くなりそうと見る（研究「AIとロジックの予想」で、作る期間だけで選んだ線）。
SLOW_SHARE = 0.20
FRONT_STYLES: tuple[str, ...] = ("逃げ", "先行")
BACK_STYLES: tuple[str, ...] = ("差し", "追込")


class SlowPaceLogic:
    """``styles`` は馬番 → 推定脚質（直近3走の脚質の中央。過去走の無い馬は入らない）、``field_size`` は頭数、``top`` は ◎ の馬番。

    AI（全頭の予想）は、レースの中の逃げ・先行の馬の数（展開）を材料にしていない。逃げ・先行が少ないと前が止まらず、
    差し・追込の ◎ は届きにくい。過去のレースでは、このレースの印の買い目を見送ると、回収率と的中率がどちらも上がった。
    """

    def skips(self, styles: Mapping[int, str], field_size: int, top: int | None) -> bool:
        """見送るか。◎ の推定脚質が無ければ見送らない。"""
        if top is None or field_size <= 0 or styles.get(top) not in BACK_STYLES:
            return False
        return self._front_count(styles) / field_size <= SLOW_SHARE

    def reason(self, styles: Mapping[int, str], field_size: int, top: int) -> str:
        """見送る理由の文。例: ``逃げ・先行が 2頭（頭数の 13%）と少なく、ペースが遅くなりそうで、◎ が差し``。"""
        front = self._front_count(styles)
        return f"逃げ・先行が {front}頭（頭数の {front / field_size:.0%}）と少なく、ペースが遅くなりそうで、◎ が{styles[top]}"

    @staticmethod
    def _front_count(styles: Mapping[int, str]) -> int:
        return sum(1 for style in styles.values() if style in FRONT_STYLES)
