"""重賞の予想の区切り（1年ずつの7つ）。"""

from __future__ import annotations

from datetime import date

from .test_window import TestWindow

#: 重賞の予想の学習データの最初の開催日（``STAKES_TABLE_PERIOD`` のサンプルの始まりと同じ）。
STAKES_DATA_FIRST_DAY = date(2012, 1, 1)

#: 重賞の予想で、過去で学習して次の1年を予想する区切り。
#:
#: 重賞は半年に約 60レース（約 900頭）しかなく、半年の区切りではログ損失や回収率が数レースの結果で大きく揺れる。
#: そのため、テストと検証を1年ずつにする（1年で約 125レース）。区切りの数は、ほかの予想の採用の基準
#: （7つのうち5つ以上）をそのまま使えるように 7つにした。テストは 2020年〜2026年（2026年は DB の最後の日まで）で、
#: 学習は 2012年1月から検証の前の年まで（いちばん短い 2020年の区切りでも7年）。
STAKES_WINDOWS: tuple[TestWindow, ...] = tuple(
    TestWindow(f"{year}年", date(year - 1, 1, 1), date(year, 1, 1), date(year, 12, 31))
    for year in range(2020, 2027)
)
