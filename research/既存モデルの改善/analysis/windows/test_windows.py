"""7つの検証の区切り（既存モデルの修正計画の 3）。"""

from __future__ import annotations

from datetime import date

from .test_window import TestWindow

#: 学習に使う最初の開催日。学習データの表（``reports/既存モデルの改善/tables``）の始まりと同じ。
DATA_FIRST_DAY = date(2017, 1, 1)

#: 過去で学習して次の半年を予想する区切り。計画の「2023年前半〜2026年前半の7期間」に合わせ、
#: 最後の区切りは 2026年の DB にある最後の日（9月）までを含める。
WINDOWS: tuple[TestWindow, ...] = (
    TestWindow("2023年前半", date(2022, 7, 1), date(2023, 1, 1), date(2023, 6, 30)),
    TestWindow("2023年後半", date(2023, 1, 1), date(2023, 7, 1), date(2023, 12, 31)),
    TestWindow("2024年前半", date(2023, 7, 1), date(2024, 1, 1), date(2024, 6, 30)),
    TestWindow("2024年後半", date(2024, 1, 1), date(2024, 7, 1), date(2024, 12, 31)),
    TestWindow("2025年前半", date(2024, 7, 1), date(2025, 1, 1), date(2025, 6, 30)),
    TestWindow("2025年後半", date(2025, 1, 1), date(2025, 7, 1), date(2025, 12, 31)),
    TestWindow("2026年", date(2025, 7, 1), date(2026, 1, 1), date(2026, 12, 31)),
)


def window_named(name: str) -> TestWindow:
    """名前から区切りを引く。知らなければ ``ValueError``。"""
    for window in WINDOWS:
        if window.name == name:
            return window
    names = " / ".join(window.name for window in WINDOWS)
    raise ValueError(f"知らない区切りです: {name}（{names}）")
