"""脚質の分け方の1通り。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleVariant:
    """脚質の分け方。``groups`` は前から後ろの順の4つで、最初の2つを「前」、残りの2つを「後ろ」とみなす。

    ``after_race`` は、レースのあとでしか分からない分け方か（True なら理解のためだけに使い、予想には使えない）。
    例: 名前「脚質（結果）」、groups = 逃げ・先行・差し・追込、前 = 逃げ・先行。
    """

    name: str
    groups: tuple[str, str, str, str]
    after_race: bool

    @property
    def front(self) -> tuple[str, str]:
        return self.groups[0], self.groups[1]

    @property
    def back(self) -> tuple[str, str]:
        return self.groups[2], self.groups[3]
