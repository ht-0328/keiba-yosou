"""TrackTendency（その日の馬場の傾向の判定と1行の文）のテスト。数は架空。"""

from __future__ import annotations

import pytest

from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.track_tendency import TrackTendency

#: いつもは 前 50%・後ろ 17%。
USUAL = PositionCounts(races=100, top3=300, front=150, middle=100, back=50)


@pytest.mark.parametrize(("today", "verdict"), [
    (PositionCounts(3, 9, 8, 1, 0), "前が止まらない"),          # 前の z = (8 − 4.5) ÷ 1.5 = 2.3
    (PositionCounts(3, 9, 6, 3, 0), "前が残り気味"),            # 前の z = 1.0
    (PositionCounts(3, 9, 2, 2, 5), "後ろから差せる"),          # 後ろの z = (5 − 1.5) ÷ 1.12 = 3.1
    (PositionCounts(2, 6, 3, 1, 2), "差しが届き気味"),          # 後ろの z = (2 − 1) ÷ 0.91 = 1.1、前の z = 0
    (PositionCounts(3, 9, 2, 6, 1), "差しが届き気味"),          # 前が少ない: 前の z = (2 − 4.5) ÷ 1.5 = −1.7
    (PositionCounts(2, 6, 4, 1, 1), "前後の偏りは目立たない"),  # 前の z = 0.8、後ろの z = 0
])
def test_前と後ろの割合をいつもと比べて_大きいほうの向きで言う(today: PositionCounts, verdict: str) -> None:
    assert TrackTendency("京都", "芝", today, USUAL).verdict() == verdict


def test_文は競馬場と芝ダ_ここまでのレース数_判定_位置の頭数_過去3年の割合() -> None:
    text = TrackTendency("京都", "芝", PositionCounts(3, 9, 8, 1, 0), USUAL).text()
    assert text == "馬場 京都・芝（ここまで3R）: 前が止まらない。3着以内9頭の4角は 前 8・中 1・後ろ 0（過去3年の京都・芝は 前 50%・中 33%・後ろ 17%）"


def test_通過順の速報待ちのレースがあれば_番号を添える() -> None:
    text = TrackTendency("京都", "芝", PositionCounts(3, 9, 8, 1, 0), USUAL, waiting=(5, 6)).text()
    assert text.endswith("後ろ 17%）。5R・6R は通過順の速報待ちで数えていない")


def test_数えたレースが無ければ_事情だけ言う() -> None:
    empty = PositionCounts(0, 0, 0, 0, 0)
    assert TrackTendency("京都", "芝", empty, empty, waiting=(5,)).text() == "馬場 京都・芝: 5R の通過順の速報がまだ届いていないので、まだ出せない"
    assert TrackTendency("京都", "ダート", empty, empty).text() == "馬場 京都・ダート: 今日のダートはこのレースが最初"
