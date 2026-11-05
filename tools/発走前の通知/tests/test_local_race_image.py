"""LocalRaceImage（地方の通知に添付する表の画像）のテスト。予想の値は架空。描けて、行の数ぶんの高さになることを見る。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_VALUE

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知 import image_style as style
from 発走前の通知.local_race_card import LocalRaceCard
from 発走前の通知.local_race_image import LocalRaceImage


def _table() -> pd.DataFrame:
    return pd.DataFrame([
        {MARK: "◎", HORSE_NO: 6, HORSE_NAME: "イチバン", WIN_ODDS: 23.0, PROBABILITY: 0.18, PLACE_VALUE: 1.30, WIN_VALUE: 1.05},
        {MARK: "○", HORSE_NO: 10, HORSE_NAME: "ニバン", WIN_ODDS: 1.9, PROBABILITY: 0.80, PLACE_VALUE: 0.88, WIN_VALUE: 0.90},
        {MARK: "－", HORSE_NO: 3, HORSE_NAME: "とてもとてもとてもとてもながいなまえのうま", WIN_ODDS: 276.5, PROBABILITY: 0.01,
         PLACE_VALUE: 0.23, WIN_VALUE: 0.54},
    ])


def _card(bets: RecommendationSet, race_day: bool = True) -> LocalRaceCard:
    return LocalRaceCard(heading="園田 5R", name="テスト特別", post="12:40 発走", timing="当日の時点", race_day=race_day,
                         table=_table(), frames={6: 5, 10: 7}, bets=bets)


def _row(ticket: str, *numbers: int) -> Recommendation:
    return Recommendation(ticket, tuple(numbers), 10.0, 0.12, 1.2)


def _height(footer_lines: int) -> int:
    return style.PAD * 2 + style.HEADER_H + style.COLUMN_H + style.ROW_H * 3 + 22 + style.FOOTER_LINE_H * footer_lines


def test_見出し_列の見出し_行_推奨買目の行と合計のぶんの高さで描く(tmp_path: Path) -> None:
    bets = RecommendationSet((_row("単勝", 6), _row("複勝", 6), _row("枠連", 3, 5)))
    image = LocalRaceImage().draw(_card(bets))
    assert image.size == (style.WIDTH, _height(3 + 1))
    image.save(tmp_path / "表.png")
    assert (tmp_path / "表.png").stat().st_size > 0


def test_長い券種の行は折り返し_理由は最後に添える() -> None:
    bets = RecommendationSet(tuple(_row("3連単", a, b, c) for a in (1, 2, 3) for b in (4, 5, 6) for c in (7, 8, 9)), "11頭未満のレース（8頭）は推奨買目の対象外")
    image = LocalRaceImage().draw(_card(bets))
    assert image.height > _height(1 + 1 + 1)   # 27点は1行に収まらないので、3連単の行が何行かに分かれる


def test_買い目が無いときは_なし_と理由の行のぶん() -> None:
    bets = RecommendationSet((), "◎ の単勝の期待値 0.90 は 1.00 未満。複勝の期待値 1.25 以上の馬はいない")
    image = LocalRaceImage().draw(_card(bets, race_day=False))
    assert image.height == _height(3)


def test_枠番の無い馬や無印でも描ける() -> None:
    card = LocalRaceCard(heading="2026110550080305（2026-11-05）の予測: 当日の時点", name="", post="", timing="当日の時点",
                         race_day=True, table=_table(), frames={}, bets=RecommendationSet((), "◎ が無い"))
    assert LocalRaceImage().draw(card).width == style.WIDTH
