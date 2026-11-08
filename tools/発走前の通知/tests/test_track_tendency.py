"""TrackTendency（その日の馬場の傾向の判定と1行の文）のテスト。数は架空。"""

from __future__ import annotations

import pytest

from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.track_tendency import TrackTendency

#: いつもは 前 50%・中 33%・後ろ 17%（位置の点数の平均 0.67、標準偏差 0.75。9頭なら z の分母は 0.25、6頭なら 0.30）。
USUAL = PositionCounts(races=100, top3=300, front=150, middle=100, back=50)
#: 後ろがほとんど来ない競馬場（地方に多い）。いつもは 前 80%・中 18%・後ろ 2%。
FRONT_TRACK = PositionCounts(races=100, top3=300, front=240, middle=54, back=6)


@pytest.mark.parametrize(("today", "verdict"), [
    (PositionCounts(3, 9, 8, 1, 0), "前が止まらない"),          # 平均 0.11: z = (0.11 − 0.67) ÷ 0.25 = −2.2
    (PositionCounts(3, 9, 6, 3, 0), "前が残り気味"),            # 平均 0.33: z = −1.3
    (PositionCounts(3, 9, 2, 2, 5), "後ろから差せる"),          # 平均 1.33: z = 2.7
    (PositionCounts(3, 9, 2, 4, 3), "差しが届き気味"),          # 平均 1.11: z = 1.8
    (PositionCounts(3, 9, 2, 6, 1), "前後の偏りは目立たない"),  # 前は少ないが後ろも多くない。平均 0.89: z = 0.9
    (PositionCounts(2, 6, 4, 1, 1), "前後の偏りは目立たない"),  # 平均 0.50: z = −0.5
])
def test_位置の点数の平均をいつもと比べて_向きと強さを言う(today: PositionCounts, verdict: str) -> None:
    assert TrackTendency("京都", "芝", today, USUAL).verdict() == verdict


def test_後ろがほとんど来ない競馬場で_前がいつもより多ければ_差しとは言わない() -> None:
    # 3着以内30頭の 前 26（87%。いつもは 80%）・後ろ 3。後ろの割合だけを比べると「後ろから差せる」になっていた形。平均 0.23: z = 0.2
    assert TrackTendency("佐賀", "ダート", PositionCounts(10, 30, 26, 1, 3), FRONT_TRACK).verdict() == "前後の偏りは目立たない"


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
