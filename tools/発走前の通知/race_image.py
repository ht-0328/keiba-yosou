"""1レースの通知の中身（中央の JraRaceCard・地方の LocalRaceCard）を、Discord に添付する表の画像に描く。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Protocol

import pandas as pd
from PIL import Image, ImageDraw

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_VALUE
from 今週の予想.mark_rule import NO_MARK, TOP_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from 発走前の通知 import image_style as style
from 発走前の通知.bet_footer import BetFooter
from 発走前の通知.local_bet_rule import WIN_VALUE_LINE

#: 列（キー・見出し・幅・寄せ l/c/r）。幅の合計と余白で画像の幅になる。
COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("mark", "印", 66, "c"), ("frame", "枠", 56, "c"), ("no", "馬番", 66, "c"), ("name", "馬名", 282, "l"), ("style", "脚質", 80, "c"), ("odds", "単勝", 110, "r"),
    ("p3", "3着以内", 210, "r"), ("place", "複勝の期待値", 152, "r"), ("win", "単勝の期待値", 152, "r"),
)
#: 文字と枠の間（px）。
GAP = 14
#: 印の札の直径、馬番の札の一辺（px）。
MARK_BADGE = 36
FRAME_BADGE = 32
#: 表と買い目の間、買い目の札の幅（px）。
FOOTER_GAP = 22
BET_PILL_W = 110
#: 買い目の1行（文・色・太字）。
FooterLine = tuple[str, style.Color, bool]
#: 値が無い（オッズがまだ無い など）ときに描く字。
MISSING = "-"
#: 買い目の行を折り返す区切り（組の間の「・」と、金額の前の「  」）。
_SEPARATORS = ("・", "  ")


class RaceCard(Protocol):
    """画像に描く中身。中央（``JraRaceCard``）と地方（``LocalRaceCard``）が同じ形で持つ。"""

    #: 場と R（例 ``園田 5R``）。
    heading: str
    #: レース名（無ければ空）。
    name: str
    #: 発走時刻（例 ``12:40 発走``。無ければ空）。
    post: str
    #: 時点（例 ``当日の時点``）。
    timing: str
    #: 当日の時点か（時点の札の色）。
    race_day: bool
    #: 印の順に並べた全頭。列名は ``今週の予想.forecast_columns``。
    table: pd.DataFrame
    #: 馬番 → 枠番。
    frames: Mapping[int, int]
    #: 馬番 → 推定脚質（逃げ・先行・差し・追込）。無い馬は「-」。
    styles: Mapping[int, str]

    @property
    def badge(self) -> str:
        """見出しの札の字（地方の ``期待度 A`` など）。空なら描かない。"""
        ...

    @property
    def footer(self) -> BetFooter: ...


class RaceImage:
    """上から 見出しの帯（場・R・レース名・発走時刻・時点の札。地方は期待度の札も）→ 列の見出し → 1頭1行（印の札・枠番（枠の色の札）・馬番・馬名・推定脚質・単勝・
    3着以内の確率の棒・複勝と単勝の期待値）→ 買い目の欄（札・券種ごとに1行。長ければ折り返す・合計・理由）。
    ◎ の行は背景と左の帯で目立たせ、線を超えた期待値は緑にする。値が無ければ「-」を描く。"""

    def draw(self, card: RaceCard) -> Image.Image:
        measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        footer = self._footer_lines(measure, card.footer)
        height = (style.PAD + style.HEADER_H + style.COLUMN_H + style.ROW_H * len(card.table) + FOOTER_GAP
                  + style.FOOTER_LINE_H * len(footer) + style.PAD)
        image = Image.new("RGB", (style.WIDTH, height), style.BG)
        draw = ImageDraw.Draw(image)
        y = self._header(draw, card, style.PAD)
        y = self._columns(draw, y)
        for _, row in card.table.iterrows():
            y = self._row(draw, row, card, y)
        self._footer(draw, card.footer.label, footer, y + FOOTER_GAP)
        return image

    # --- 見出しの帯 ---------------------------------------------------------------------------

    def _header(self, draw: ImageDraw.ImageDraw, card: RaceCard, y: int) -> int:
        left, right = style.PAD, style.WIDTH - style.PAD
        draw.rounded_rectangle([(left, y), (right, y + style.HEADER_H)], radius=18, fill=style.HEADER_BG)
        draw.text((left + 26, y + 22), card.heading, font=style.font(40, bold=True), fill=style.TEXT, anchor="la")
        name = self._fit(draw, card.name, style.font(22), right - left - 52 - 320)
        draw.text((left + 26, y + 84), name, font=style.font(22), fill=style.DIM, anchor="la")
        post_font = style.font(28, bold=True)
        draw.text((right - 26, y + 26), card.post, font=post_font, fill=style.TEXT, anchor="ra")
        if card.badge:
            # 期待度の札は発走時刻の左（上の段。下の段の時点の札はレース名と並ぶので、長い時点の文と重ならないように）
            fill, color = style.GRADE_PILLS.get(card.badge[-1], (style.LINE, style.DIM))
            self._pill(draw, card.badge, right - 26 - round(draw.textlength(card.post, font=post_font)) - GAP * 2, y + 24, fill, color, align="r")
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

    def _row(self, draw: ImageDraw.ImageDraw, row: pd.Series, card: RaceCard, y: int) -> int:
        top = row[MARK] == TOP_MARK
        background = style.TOP_ROW_BG if top else style.BG
        if top:
            draw.rectangle([(style.PAD, y), (style.WIDTH - style.PAD, y + style.ROW_H)], fill=background)
            draw.rounded_rectangle([(style.PAD, y + 8), (style.PAD + 5, y + style.ROW_H - 8)], radius=2, fill=style.GOLD)
        center = y + style.ROW_H // 2
        x = style.PAD
        for key, _, width, align in COLUMNS:
            self._cell(draw, key, row, card, x, center, width, align, top, background)
            x += width
        bottom = y + style.ROW_H
        draw.line([(style.PAD, bottom), (style.WIDTH - style.PAD, bottom)], fill=style.LINE, width=1)
        return bottom

    def _cell(self, draw: ImageDraw.ImageDraw, key: str, row: pd.Series, card: RaceCard, x: int, center: int,
              width: int, align: str, top: bool, background: style.Color) -> None:
        if key == "mark":
            self._mark_badge(draw, str(row[MARK]), x + width // 2, center)
        elif key == "frame":
            frame = card.frames.get(int(row[HORSE_NO])) if _known(row[HORSE_NO]) else None
            if frame is None:
                self._text(draw, MISSING, x, center, width, align, style.font(22), style.DIM)
            else:
                self._frame_badge(draw, frame, x + width // 2, center)
        elif key == "no":
            number = str(int(row[HORSE_NO])) if _known(row[HORSE_NO]) else MISSING
            self._text(draw, number, x, center, width, align, style.font(23, bold=True), style.TEXT if number != MISSING else style.DIM)
        elif key == "name":
            name = self._fit(draw, str(row[HORSE_NAME]), style.font(23, bold=top), width - GAP * 2)
            self._text(draw, name, x, center, width, align, style.font(23, bold=top), style.TEXT)
        elif key == "style":
            running = card.styles.get(int(row[HORSE_NO])) if _known(row[HORSE_NO]) else None
            color = style.STYLE_COLORS.get(running or "", style.DIM)
            self._text(draw, running or MISSING, x, center, width, align, style.font(21, bold=True), color)
        elif key == "odds":
            self._text(draw, _number(row[WIN_ODDS], 1), x, center, width, align, style.font(23), style.TEXT)
        elif key == "p3":
            self._probability(draw, float(row[PROBABILITY]), x, center, width, top, background)
        elif key == "place":
            self._value(draw, row[PLACE_VALUE], x, center, width, _at_least(row[PLACE_VALUE], PLACE_VALUE_LINE))
        elif key == "win":
            self._value(draw, row[WIN_VALUE], x, center, width, top and _at_least(row[WIN_VALUE], WIN_VALUE_LINE))

    def _mark_badge(self, draw: ImageDraw.ImageDraw, mark: str, cx: int, cy: int) -> None:
        color = style.MARK_COLORS.get(mark)
        if color is None or mark == NO_MARK:
            draw.text((cx, cy), mark, font=style.font(22), fill=style.DIM, anchor="mm")
            return
        r = MARK_BADGE // 2
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
        draw.text((cx, cy - 1), mark, font=style.font(21, bold=True), fill=style.TEXT, anchor="mm")

    def _frame_badge(self, draw: ImageDraw.ImageDraw, frame: int, cx: int, cy: int) -> None:
        """枠の色の札に枠番を書く。"""
        color = style.FRAME_COLORS.get(frame, style.FRAME_UNKNOWN)
        fill = style.BG if frame in style.FRAME_DARK_TEXT else style.TEXT
        r = FRAME_BADGE // 2
        draw.rounded_rectangle([(cx - r, cy - r), (cx + r, cy + r)], radius=7, fill=color, outline=style.LINE, width=1)
        draw.text((cx, cy - 1), str(frame), font=style.font(20, bold=True), fill=fill, anchor="mm")

    def _probability(self, draw: ImageDraw.ImageDraw, probability: float, x: int, center: int, width: int, top: bool,
                     background: style.Color) -> None:
        # 棒は左側に収め、右の数字（最大 100% で 70px）と重ねない
        inner = width - GAP * 2 - 70
        bar_w = max(4, round(inner * min(max(probability, 0.0), 1.0)))
        bar = style.blend(background, style.GOLD if top else style.BAR, 0.45)
        draw.rounded_rectangle([(x + GAP, center - 14), (x + GAP + bar_w, center + 14)], radius=6, fill=bar)
        self._text(draw, f"{probability:.0%}", x, center, width, "r", style.font(23, bold=top), style.TEXT)

    def _value(self, draw: ImageDraw.ImageDraw, value: object, x: int, center: int, width: int, good: bool) -> None:
        fill = style.GOOD if good else style.TEXT
        self._text(draw, _number(value, 2), x, center, width, "r", style.font(23, bold=good), fill)

    # --- 買い目の欄 ---------------------------------------------------------------------------

    def _footer_lines(self, draw: ImageDraw.ImageDraw, footer: BetFooter) -> list[FooterLine]:
        """買い目の欄の行（文・色・太字）。券種の行は幅に収まるよう括弧の外の区切りで折り返し、合計、理由（幅で折り返す）。
        無ければ「なし」と理由。"""
        max_width = style.WIDTH - style.PAD * 2 - BET_PILL_W - GAP
        notes = [(part, style.DIM, False) for note in footer.notes
                 for part in self._wrap_chars(draw, f"・{note}", style.font(22), max_width)]
        if footer.none:
            return [("なし", style.DIM, True), *notes]
        lines: list[FooterLine] = []
        for line in footer.lines:
            lines += [(part, style.TEXT, True) for part in self._wrap(draw, line, style.font(22, bold=True), max_width)]
        if footer.total:
            lines.append((footer.total, style.GOLD, True))
        return lines + notes

    def _footer(self, draw: ImageDraw.ImageDraw, label: str, lines: list[FooterLine], y: int) -> None:
        self._pill(draw, label, style.PAD, y, style.GOLD, style.BG, align="l")
        x = style.PAD + BET_PILL_W + GAP
        for index, (text, fill, bold) in enumerate(lines):
            draw.text((x, y + 16 + style.FOOTER_LINE_H * index), text, font=style.font(22, bold=bold), fill=fill, anchor="lm")

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, line: str, font, max_width: int) -> list[str]:
        """括弧の外の「・」と「  」（金額の前）の区切りで折り返す。2行目からは券種の名前のぶん字下げする。"""
        head, _, body = line.partition(" ")
        rows: list[str] = []
        current = head
        for separator, part in RaceImage._parts(body):
            candidate = f"{current} {part}" if current == head else f"{current}{separator}{part}"
            if draw.textlength(candidate, font=font) <= max_width or current == head:
                current = candidate
                continue
            rows.append(current)
            current = f"{'　' * len(head)} {part}"
        rows.append(current)
        return rows

    @staticmethod
    def _parts(body: str) -> list[tuple[str, str]]:
        """（前の区切り, 部分）の並び。括弧（（）の中の「・」では分けない（中央の「期待値 1.18・オッズ 10.9」）。"""
        parts: list[tuple[str, str]] = []
        depth, start, separator, index = 0, 0, "", 0
        while index < len(body):
            char = body[index]
            if char in "（(":
                depth += 1
            elif char in "）)":
                depth -= 1
            elif depth == 0 and body.startswith(_SEPARATORS, index):
                found = next(mark for mark in _SEPARATORS if body.startswith(mark, index))
                parts.append((separator, body[start:index]))
                separator, start = found, index + len(found)
                index = start
                continue
            index += 1
        parts.append((separator, body[start:]))
        return parts

    @staticmethod
    def _wrap_chars(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
        """区切りの無い文（理由）を、幅に収まるよう字で折り返す。2行目からは1字下げる。"""
        rows: list[str] = []
        current = ""
        for char in text:
            if current and draw.textlength(current + char, font=font) > max_width:
                rows.append(current)
                current = f"　{char}"
            else:
                current += char
        rows.append(current)
        return rows

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


def _known(value: object) -> bool:
    return isinstance(value, (int, float)) and not math.isnan(value)


def _number(value: object, digits: int) -> str:
    """数を小数 ``digits`` 桁で。無い（None・NaN）なら「-」。"""
    return f"{value:.{digits}f}" if _known(value) else MISSING


def _at_least(value: object, line: float) -> bool:
    return _known(value) and value >= line  # type: ignore[operator]
