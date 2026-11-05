"""地方の1レースの通知の中身（LocalRaceCard）を、Discord に添付する表の画像に描く。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from PIL import Image, ImageDraw

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_VALUE
from 今週の予想.mark_rule import NO_MARK, TOP_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from 発走前の通知 import image_style as style
from 発走前の通知.local_bet_rule import WIN_VALUE_LINE
from 発走前の通知.local_bets import LocalBets
from 発走前の通知.local_race_card import LocalRaceCard

#: 列（キー・見出し・幅・寄せ l/c/r）。幅の合計と余白で画像の幅になる。
COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("mark", "印", 66, "c"), ("no", "馬番", 72, "c"), ("name", "馬名", 282, "l"), ("odds", "単勝", 110, "r"),
    ("p3", "3着以内", 210, "r"), ("place", "複勝の期待値", 152, "r"), ("win", "単勝の期待値", 152, "r"),
)
#: 文字と枠の間（px）。
GAP = 14
#: 印の札の直径、馬番の札の一辺（px）。
MARK_BADGE = 36
FRAME_BADGE = 32
#: 見出しの帯と買い目の間、買い目の札の幅（px）。
FOOTER_GAP = 22
BET_PILL_W = 96


class LocalRaceImage:
    """上から 見出しの帯（場・R・レース名・発走時刻・時点の札）→ 列の見出し → 1頭1行（印の札・枠の色の馬番・馬名・単勝・
    3着以内の確率の棒・複勝と単勝の期待値）→ 買い目。◎ の行は背景と左の帯で目立たせ、線を超えた期待値は緑にする。"""

    def draw(self, card: LocalRaceCard) -> Image.Image:
        footer_lines = len(card.bets.lines) if not card.bets.none else 1 + len(card.bets.reasons)
        height = (style.PAD + style.HEADER_H + style.COLUMN_H + style.ROW_H * len(card.table) + FOOTER_GAP
                  + style.FOOTER_LINE_H * footer_lines + style.PAD)
        image = Image.new("RGB", (style.WIDTH, height), style.BG)
        draw = ImageDraw.Draw(image)
        y = self._header(draw, card, style.PAD)
        y = self._columns(draw, y)
        for _, row in card.table.iterrows():
            y = self._row(draw, row, card.frames, y)
        self._footer(draw, card.bets, y + FOOTER_GAP)
        return image

    # --- 見出しの帯 ---------------------------------------------------------------------------

    def _header(self, draw: ImageDraw.ImageDraw, card: LocalRaceCard, y: int) -> int:
        left, right = style.PAD, style.WIDTH - style.PAD
        draw.rounded_rectangle([(left, y), (right, y + style.HEADER_H)], radius=18, fill=style.HEADER_BG)
        draw.text((left + 26, y + 22), card.heading, font=style.font(40, bold=True), fill=style.TEXT, anchor="la")
        name = self._fit(draw, card.name, style.font(22), right - left - 52 - 320)
        draw.text((left + 26, y + 84), name, font=style.font(22), fill=style.DIM, anchor="la")
        draw.text((right - 26, y + 26), card.post, font=style.font(28, bold=True), fill=style.TEXT, anchor="ra")
        pill = style.RACE_DAY_PILL if card.race_day else style.EVE_PILL
        self._pill(draw, card.timing, right - 26, y + 78, pill, style.TEXT, align="r")
        return y + style.HEADER_H

    # --- 列の見出し ---------------------------------------------------------------------------

    def _columns(self, draw: ImageDraw.ImageDraw, y: int) -> int:
        x = style.PAD
        for _, label, width, align in COLUMNS:
            self._text(draw, label, x, y + style.COLUMN_H // 2, width, align, style.font(18), style.DIM)
            x += width
        bottom = y + style.COLUMN_H
        draw.line([(style.PAD, bottom), (style.WIDTH - style.PAD, bottom)], fill=style.LINE, width=2)
        return bottom

    # --- 1頭の行 ---------------------------------------------------------------------------

    def _row(self, draw: ImageDraw.ImageDraw, row: pd.Series, frames: Mapping[int, int], y: int) -> int:
        top = row[MARK] == TOP_MARK
        background = style.TOP_ROW_BG if top else style.BG
        if top:
            draw.rectangle([(style.PAD, y), (style.WIDTH - style.PAD, y + style.ROW_H)], fill=background)
            draw.rounded_rectangle([(style.PAD, y + 8), (style.PAD + 5, y + style.ROW_H - 8)], radius=2, fill=style.GOLD)
        center = y + style.ROW_H // 2
        x = style.PAD
        for key, _, width, align in COLUMNS:
            self._cell(draw, key, row, frames, x, center, width, align, top, background)
            x += width
        bottom = y + style.ROW_H
        draw.line([(style.PAD, bottom), (style.WIDTH - style.PAD, bottom)], fill=style.LINE, width=1)
        return bottom

    def _cell(self, draw: ImageDraw.ImageDraw, key: str, row: pd.Series, frames: Mapping[int, int], x: int, center: int,
              width: int, align: str, top: bool, background: style.Color) -> None:
        if key == "mark":
            self._mark_badge(draw, str(row[MARK]), x + width // 2, center)
        elif key == "no":
            self._frame_badge(draw, int(row[HORSE_NO]), frames.get(int(row[HORSE_NO])), x + width // 2, center)
        elif key == "name":
            name = self._fit(draw, str(row[HORSE_NAME]), style.font(23, bold=top), width - GAP * 2)
            self._text(draw, name, x, center, width, align, style.font(23, bold=top), style.TEXT)
        elif key == "odds":
            self._text(draw, f"{row[WIN_ODDS]:.1f}", x, center, width, align, style.font(23), style.TEXT)
        elif key == "p3":
            self._probability(draw, float(row[PROBABILITY]), x, center, width, top, background)
        elif key == "place":
            good = row[PLACE_VALUE] >= PLACE_VALUE_LINE
            self._value(draw, float(row[PLACE_VALUE]), x, center, width, good)
        elif key == "win":
            self._value(draw, float(row[WIN_VALUE]), x, center, width, top and row[WIN_VALUE] >= WIN_VALUE_LINE)

    def _mark_badge(self, draw: ImageDraw.ImageDraw, mark: str, cx: int, cy: int) -> None:
        color = style.MARK_COLORS.get(mark)
        if color is None or mark == NO_MARK:
            draw.text((cx, cy), mark, font=style.font(22), fill=style.DIM, anchor="mm")
            return
        r = MARK_BADGE // 2
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
        draw.text((cx, cy - 1), mark, font=style.font(21, bold=True), fill=style.TEXT, anchor="mm")

    def _frame_badge(self, draw: ImageDraw.ImageDraw, horse_no: int, frame: int | None, cx: int, cy: int) -> None:
        color = style.FRAME_COLORS.get(frame or 0, style.FRAME_UNKNOWN)
        fill = style.BG if frame in style.FRAME_DARK_TEXT else style.TEXT
        r = FRAME_BADGE // 2
        draw.rounded_rectangle([(cx - r, cy - r), (cx + r, cy + r)], radius=7, fill=color, outline=style.LINE, width=1)
        draw.text((cx, cy - 1), str(horse_no), font=style.font(20, bold=True), fill=fill, anchor="mm")

    def _probability(self, draw: ImageDraw.ImageDraw, probability: float, x: int, center: int, width: int, top: bool,
                     background: style.Color) -> None:
        # 棒は左側に収め、右の数字（最大 100% で 70px）と重ねない
        inner = width - GAP * 2 - 70
        bar_w = max(4, round(inner * min(max(probability, 0.0), 1.0)))
        bar = style.blend(background, style.GOLD if top else style.BAR, 0.45)
        draw.rounded_rectangle([(x + GAP, center - 14), (x + GAP + bar_w, center + 14)], radius=6, fill=bar)
        self._text(draw, f"{probability:.0%}", x, center, width, "r", style.font(23, bold=top), style.TEXT)

    def _value(self, draw: ImageDraw.ImageDraw, value: float, x: int, center: int, width: int, good: bool) -> None:
        fill = style.GOOD if good else style.TEXT
        self._text(draw, f"{value:.2f}", x, center, width, "r", style.font(23, bold=good), fill)

    # --- 買い目 ---------------------------------------------------------------------------

    def _footer(self, draw: ImageDraw.ImageDraw, bets: LocalBets, y: int) -> None:
        self._pill(draw, "買い目", style.PAD, y, style.GOLD, style.BG, align="l")
        x = style.PAD + BET_PILL_W + GAP
        if not bets.none:
            self._lines(draw, bets.lines, x, y, style.TEXT, bold=True)
            return
        draw.text((x, y + 16), "なし", font=style.font(22, bold=True), fill=style.DIM, anchor="lm")
        self._lines(draw, [f"・{reason}" for reason in bets.reasons], x, y + style.FOOTER_LINE_H, style.DIM, bold=False)

    def _lines(self, draw: ImageDraw.ImageDraw, lines, x: int, y: int, fill: style.Color, *, bold: bool) -> None:
        for index, line in enumerate(lines):
            draw.text((x, y + 16 + style.FOOTER_LINE_H * index), line, font=style.font(22, bold=bold), fill=fill, anchor="lm")

    # --- 共通の描き方 ---------------------------------------------------------------------------

    @staticmethod
    def _text(draw: ImageDraw.ImageDraw, text: str, x: int, center: int, width: int, align: str, font, fill: style.Color) -> None:
        """セルの中に寄せて描く（l: 左、c: 中央、r: 右）。"""
        if align == "r":
            draw.text((x + width - GAP, center), text, font=font, fill=fill, anchor="rm")
        elif align == "c":
            draw.text((x + width // 2, center), text, font=font, fill=fill, anchor="mm")
        else:
            draw.text((x + GAP, center), text, font=font, fill=fill, anchor="lm")

    @staticmethod
    def _pill(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, fill: style.Color, color: style.Color, *, align: str) -> None:
        """角の丸い札（高さ 32）。``align`` が r なら ``x`` を右端にする。"""
        font = style.font(18, bold=True)
        width = max(BET_PILL_W, round(draw.textlength(text, font=font)) + 32)
        left = x - width if align == "r" else x
        draw.rounded_rectangle([(left, y), (left + width, y + 32)], radius=16, fill=fill)
        draw.text((left + width // 2, y + 15), text, font=font, fill=color, anchor="mm")

    @staticmethod
    def _fit(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
        """幅に収まらない文は末尾を … にする。"""
        if draw.textlength(text, font=font) <= max_width:
            return text
        kept = text
        while kept and draw.textlength(kept + "…", font=font) > max_width:
            kept = kept[:-1]
        return kept + "…"
