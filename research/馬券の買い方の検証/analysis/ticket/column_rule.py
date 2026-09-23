"""フォーメーションの1列の指定。"""

from __future__ import annotations

from dataclasses import dataclass

from .picker.candidate_picker import CandidatePicker


@dataclass(frozen=True)
class ColumnRule:
    """1列に何頭を、どう選んで置くか。

    - ``picker``: 候補の選び方（近走の順・穴馬の順・人気順位 …）。
    - ``count``: この列の頭数（``keeps_previous`` のときは、前の列の馬を含めた頭数）。
    - ``keeps_previous``: 前の列の馬をそのまま含め、残りを ``picker`` で足す（「3列目は2列目 + 押さえ2頭」の形）。
    - ``same_as``: 先の列の番号（0 始まり）を指すと、その列と同じ馬番にする（「3着は1着と同じ4頭」の形）。``picker`` は使わない。
    """

    picker: CandidatePicker
    count: int
    keeps_previous: bool = False
    same_as: int | None = None

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError(f"列の頭数は1以上です: {self.count}")
