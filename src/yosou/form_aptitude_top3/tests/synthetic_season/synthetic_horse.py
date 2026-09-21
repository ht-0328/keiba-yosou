"""架空の馬1頭。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticHorse:
    """架空の馬。``ability`` が高いほど上位に来やすい。騎手・調教師・性別は、番号から決まる。"""

    number: int
    ability: float

    @property
    def hid(self) -> str:
        """血統登録番号（10桁）。"""
        return f"2020{self.number:06d}"

    @property
    def name(self) -> str:
        return f"ウマ{self.number:03d}"

    @property
    def sex_code(self) -> str:
        """性別コード。3頭に1頭が牝（2）、ほかは牡（1）。"""
        return "2" if self.number % 3 == 0 else "1"

    @property
    def jockey(self) -> tuple[str, str]:
        """（騎手コード, 騎手名）。騎手は 12人。"""
        code = self.number % 12 + 1
        return f"{code:05d}", f"騎手{code}"

    @property
    def trainer(self) -> tuple[str, str]:
        """（調教師コード, 調教師名）。調教師は 7人。"""
        code = self.number % 7 + 1
        return f"{code:05d}", f"調教師{code}"

    @property
    def trains_on_wood(self) -> bool:
        """ウッドで調教するか。3頭に1頭がウッド、ほかは坂路。"""
        return self.number % 3 == 1
