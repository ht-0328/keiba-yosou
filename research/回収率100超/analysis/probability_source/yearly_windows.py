"""年ごとの区切り（予想のパッケージの学習部品が受け取る形）。"""

from __future__ import annotations

from datetime import date

from 既存モデルの改善.analysis.windows import TestWindow


class YearlyWindows:
    """この研究の年ごとの区切り（``WalkForwardYears``）を、研究「既存モデルの改善」の ``TestWindow`` の並びにする。

    分け方は ``WalkForwardYears`` と同じ: その年より前で学習し、直前の1年で木の本数を決め（学習には使わない）、
    その年を予測する。研究「既存モデルの改善」の半年ごとの7つの区切り（2023年前半〜2026年）ではなく、こちらに
    そろえるのは、複勝の線を前半（2019〜2021年）だけで選ぶ決まりを元の方法と同じに保つためである
    （7つの区切りは 2023年からしか予測が無く、前半の年が無い）。
    """

    def __init__(self, first_test_year: int, last_test_year: int) -> None:
        if first_test_year > last_test_year:
            raise ValueError(f"最初の年（{first_test_year}）が最後の年（{last_test_year}）より後です")
        self._first_test_year = first_test_year
        self._last_test_year = last_test_year

    def build(self) -> tuple[TestWindow, ...]:
        return tuple(TestWindow(f"{year}年", date(year - 1, 1, 1), date(year, 1, 1), date(year, 12, 31))
                     for year in range(self._first_test_year, self._last_test_year + 1))
