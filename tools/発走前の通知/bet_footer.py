"""表の画像の下に描く買い目の欄（札の名前・買い目の行・合計・添える理由）。中央と地方の両方が同じ形で渡す。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BetFooter:
    #: 欄の左の札の文字（例 ``推奨買目``・``買い目``）。
    label: str
    #: 券種ごとの買い目の行（長い行は画像の側で「・」の区切りで折り返す）。無ければ空で、画像には「なし」と描く。
    lines: tuple[str, ...] = ()
    #: 合計の行（例 ``合計 12点 1,200円（1点 100円）``）。買い目が無ければ空。
    total: str = ""
    #: 添える理由（1つ1行）。
    notes: tuple[str, ...] = ()

    @property
    def none(self) -> bool:
        return not self.lines
