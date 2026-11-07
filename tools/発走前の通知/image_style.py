"""表の画像の見た目（大きさ・色・字体）。Discord の暗い画面に合わせた配色。"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PIL import ImageFont

#: 画像の幅と余白（px）。
WIDTH = 1230
PAD = 28
#: 見出しの帯・列の見出し・1頭の行・買い目の1行の高さ（px）。
HEADER_H = 124
COLUMN_H = 44
ROW_H = 52
FOOTER_LINE_H = 34

#: 字体（Windows の游ゴシック。無ければ PIL の標準の字体）。
FONT_DIR = Path(r"C:\Windows\Fonts")
REGULAR = "YuGothM.ttc"
BOLD = "YuGothB.ttc"

Color = tuple[int, int, int]

#: 背景と文字。
BG: Color = (22, 24, 31)
HEADER_BG: Color = (36, 40, 62)
TEXT: Color = (232, 234, 240)
DIM: Color = (142, 149, 166)
LINE: Color = (46, 50, 64)
#: ◎ の行の背景と左の帯。
TOP_ROW_BG: Color = (44, 46, 72)
GOLD: Color = (240, 184, 64)
#: 3着以内の確率の棒。
BAR: Color = (62, 108, 176)
#: 期待値が線を超えた数字。
GOOD: Color = (82, 220, 130)
#: 時点の札（当日 / 前日）。
RACE_DAY_PILL: Color = (34, 150, 96)
EVE_PILL: Color = (190, 120, 30)

#: 枠番の色（1 白・2 黒・3 赤・4 青・5 黄・6 緑・7 橙・8 桃）と、黒い字にする枠。
FRAME_COLORS: dict[int, Color] = {
    1: (244, 244, 244), 2: (34, 34, 38), 3: (216, 40, 62), 4: (40, 104, 190),
    5: (246, 208, 46), 6: (40, 160, 92), 7: (238, 136, 40), 8: (238, 150, 190),
}
FRAME_DARK_TEXT = frozenset({1, 5, 8})
FRAME_UNKNOWN: Color = (70, 74, 90)

#: 印の札の色。無印は札を付けない。消（中央の危険な人気馬）は暗い色の札にして、買う印と見分ける。
MARK_COLORS: dict[str, Color] = {
    "◎": (228, 64, 76), "○": (58, 128, 240), "▲": (38, 186, 96), "△": (104, 118, 142),
    "☆": (238, 160, 32), "注": (140, 96, 236), "消": (84, 62, 70),
}
#: 推定脚質の字の色（前に行く脚質ほど暖かい色）。
STYLE_COLORS: dict[str, Color] = {
    "逃げ": (240, 104, 104), "先行": (240, 168, 72), "差し": (96, 166, 240), "追込": (168, 132, 236),
}


@cache
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_DIR / (BOLD if bold else REGULAR)
    if path.is_file():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def blend(base: Color, over: Color, amount: float) -> Color:
    """``base`` に ``over`` を ``amount``（0〜1）だけ重ねた色。"""
    return tuple(round(b + (o - b) * amount) for b, o in zip(base, over, strict=True))  # type: ignore[return-value]
