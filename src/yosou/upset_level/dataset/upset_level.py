"""荒れ具合を表す値。"""

from __future__ import annotations

from enum import Enum


class UpsetLevel(Enum):
    """荒れ具合の4段階（設計書 10）。値はクラスの番号（0〜3）で、目的変数とモデルの出力の列の順になる。"""

    SOLID = 0
    MID = 1
    BIG = 2
    HUGE = 3

    @property
    def label(self) -> str:
        """人が読む名前（固い・中荒れ・大荒れ・超荒れ）。"""
        return _LABELS[self]

    @classmethod
    def labels(cls) -> tuple[str, ...]:
        """クラスの番号の順の名前。"""
        return tuple(level.label for level in cls)

    @classmethod
    def class_labels(cls) -> tuple[int, ...]:
        """クラスの番号の並び（学習データの ``class_labels``）。"""
        return tuple(level.value for level in cls)


_LABELS: dict[UpsetLevel, str] = {
    UpsetLevel.SOLID: "固い", UpsetLevel.MID: "中荒れ", UpsetLevel.BIG: "大荒れ", UpsetLevel.HUGE: "超荒れ",
}
