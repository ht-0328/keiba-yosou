"""RaceImage（中央と地方の通知に添付する表の画像）のテスト。予想の値は架空。描けて、行の数ぶんの高さになることを見る。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_VALUE

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知 import image_style as style
from 発走前の通知.jra_race_card import JraRaceCard
from 発走前の通知.local_expectation import LocalExpectation
from 発走前の通知.local_race_card import LocalRaceCard
from 発走前の通知.race_image import RaceImage


def _table() -> pd.DataFrame:
    return pd.DataFrame([
        {MARK: "◎", HORSE_NO: 6, HORSE_NAME: "イチバン", WIN_ODDS: 23.0, PROBABILITY: 0.18, PLACE_VALUE: 1.30, WIN_VALUE: 1.05},
        {MARK: "○", HORSE_NO: 10, HORSE_NAME: "ニバン", WIN_ODDS: 1.9, PROBABILITY: 0.80, PLACE_VALUE: 0.88, WIN_VALUE: 0.90},
        {MARK: "－", HORSE_NO: 3, HORSE_NAME: "とてもとてもとてもとてもながいなまえのうま", WIN_ODDS: 276.5, PROBABILITY: 0.01,
         PLACE_VALUE: 0.23, WIN_VALUE: 0.54},
    ])


def _card(bets: RecommendationSet, race_day: bool = True, expectation: LocalExpectation | None = None) -> LocalRaceCard:
    return LocalRaceCard(heading="園田 5R", name="テスト特別", post="12:40 発走", timing="当日の時点", race_day=race_day,
                         table=_table(), frames={6: 5, 10: 7}, bets=bets, expectation=expectation or LocalExpectation(0.21, "A"))


def _row(ticket: str, *numbers: int) -> Recommendation:
    return Recommendation(ticket, tuple(numbers), 10.0, 0.12, 1.2)


def _height(footer_lines: int) -> int:
    return style.PAD * 2 + style.HEADER_H + style.COLUMN_H + style.ROW_H * 3 + 22 + style.FOOTER_LINE_H * footer_lines


def test_見出し_列の見出し_行_推奨買目の行と合計のぶんの高さで描く(tmp_path: Path) -> None:
    bets = RecommendationSet((_row("単勝", 6), _row("複勝", 6), _row("枠連", 3, 5)))
    image = RaceImage().draw(_card(bets))
    assert image.size == (style.WIDTH, _height(3 + 1))
    image.save(tmp_path / "表.png")
    assert (tmp_path / "表.png").stat().st_size > 0


def test_長い券種の行は折り返し_理由は最後に添える() -> None:
    bets = RecommendationSet(tuple(_row("3連単", a, b, c) for a in (1, 2, 3) for b in (4, 5, 6) for c in (7, 8, 9)), "11頭未満のレース（8頭）は推奨買目の対象外")
    image = RaceImage().draw(_card(bets))
    assert image.height > _height(1 + 1 + 1)   # 27点は1行に収まらないので、3連単の行が何行かに分かれる


def test_期待度の札は見出しの発走時刻の左に描き_無ければ描かない() -> None:
    bets = RecommendationSet((_row("単勝", 6),))
    with_badge = RaceImage().draw(_card(bets, expectation=LocalExpectation(0.50, "S")))
    without = RaceImage().draw(_card(bets, expectation=LocalExpectation(None, None)))
    assert with_badge.size == without.size
    # 札は上の段（見出しの帯の中、発走時刻の左）。その帯の中の色が変わり、下の表は同じ
    header = (style.PAD, style.PAD, style.WIDTH - style.PAD, style.PAD + style.HEADER_H)
    assert with_badge.crop(header).tobytes() != without.crop(header).tobytes()
    below = (0, style.PAD + style.HEADER_H, style.WIDTH, with_badge.height)
    assert with_badge.crop(below).tobytes() == without.crop(below).tobytes()
    assert _card(bets).badge == "期待度 A" and _card(bets, expectation=LocalExpectation(None, None)).badge == ""


def test_列の幅は画像の幅に収まる() -> None:
    from 発走前の通知.race_image import COLUMNS
    assert sum(width for _, _, width, _ in COLUMNS) == style.WIDTH - style.PAD * 2


def test_馬名の右に推定脚質を脚質の色で描き_無い馬は横線() -> None:
    from 発走前の通知.race_image import COLUMNS
    card = LocalRaceCard(heading="園田 5R", name="", post="", timing="当日の時点", race_day=True, table=_table(), frames={},
                         bets=RecommendationSet((), "なし"), styles={6: "逃げ", 10: "追込"})
    image = RaceImage().draw(card).convert("RGB")
    left = style.PAD + sum(width for key, _, width, _ in COLUMNS[:[key for key, *_ in COLUMNS].index("style")])
    width = next(width for key, _, width, _ in COLUMNS if key == "style")

    def colors(row: int) -> set:
        top = style.PAD + style.HEADER_H + style.COLUMN_H + style.ROW_H * row
        return {image.getpixel((x, y)) for x in range(left, left + width) for y in range(top + 4, top + style.ROW_H - 4)}

    assert style.STYLE_COLORS["逃げ"] in colors(0)
    assert style.STYLE_COLORS["追込"] in colors(1)
    assert not set(style.STYLE_COLORS.values()) & colors(2)   # 3番は脚質が無いので「-」（色を付けない）


def test_馬番の左に枠番を枠の色の札で描き_枠番の無い馬は横線() -> None:
    from 発走前の通知.race_image import COLUMNS
    image = RaceImage().draw(_card(RecommendationSet((), "なし"))).convert("RGB")
    keys = [key for key, *_ in COLUMNS]
    left = style.PAD + sum(width for _, _, width, _ in COLUMNS[:keys.index("frame")])
    width = COLUMNS[keys.index("frame")][2]

    def colors(row: int) -> set:
        top = style.PAD + style.HEADER_H + style.COLUMN_H + style.ROW_H * row
        return {image.getpixel((x, y)) for x in range(left, left + width) for y in range(top + 4, top + style.ROW_H - 4)}

    assert style.FRAME_COLORS[5] in colors(0)   # 6番は5枠（黄）
    assert style.FRAME_COLORS[7] in colors(1)   # 10番は7枠（橙）
    assert not set(style.FRAME_COLORS.values()) & colors(2)   # 3番は枠番が無いので「-」


def test_買い目が無いときは_なし_と理由の行のぶん() -> None:
    bets = RecommendationSet((), "◎ の単勝の期待値 0.90 は 1.00 未満。複勝の期待値 1.25 以上の馬はいない")
    image = RaceImage().draw(_card(bets, race_day=False))
    assert image.height == _height(3)


def test_枠番の無い馬や無印でも描ける() -> None:
    card = LocalRaceCard(heading="2026110550080305（2026-11-05）の予測: 当日の時点", name="", post="", timing="当日の時点",
                         race_day=True, table=_table(), frames={}, bets=RecommendationSet((), "◎ が無い"))
    assert RaceImage().draw(card).width == style.WIDTH


def _jra_card(bets: tuple[tuple[str, int], ...], notes: tuple[str, ...] = ()) -> JraRaceCard:
    table = pd.concat([_table(), pd.DataFrame([
        {MARK: "消", HORSE_NO: 8, HORSE_NAME: "キケン", WIN_ODDS: 2.4, PROBABILITY: 0.35, PLACE_VALUE: 0.80, WIN_VALUE: 0.70},
        {MARK: "－", HORSE_NO: float("nan"), HORSE_NAME: "バンゴウナシ", WIN_ODDS: float("nan"), PROBABILITY: 0.02,
         PLACE_VALUE: float("nan"), WIN_VALUE: None},
    ])], ignore_index=True)
    return JraRaceCard(heading="京都 11R", name="みやこＳ", post="15:35 発走", timing="当日の時点", race_day=True,
                       grades="期待度 A（点数 0.28）", table=table, frames={6: 5, 8: 6}, bets=bets, notes=notes)


def test_中央は消の札と_値の無い馬も描き_買い目の行と合計のぶんの高さ() -> None:
    card = _jra_card((("複勝（勝負）: 6 イチバン（期待値 1.30、1,000円）  合計 1,000円", 1000), ("単勝: 6（オッズ 23.0）  1点 100円 × 1点 = 100円", 100)))
    assert card.footer.total == "合計 1,100円"
    image = RaceImage().draw(card)
    assert image.size == (style.WIDTH, _height(2 + 1) + style.ROW_H * 2)


def test_中央で買わないときは_なし_と理由() -> None:
    image = RaceImage().draw(_jra_card((), ("勝負レースでない",)))
    assert image.height == _height(2) + style.ROW_H * 2
