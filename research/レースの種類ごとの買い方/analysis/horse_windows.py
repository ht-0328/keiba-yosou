"""手順4 で馬の予想モデルを学び直す23の区切り（docs/01 の 7）。"""

from __future__ import annotations

from datetime import date

from 既存モデルの改善.analysis.windows import TestWindow

from 複勝以外の回収率100超.analysis.early_windows import OLDEST_WINDOWS

#: 2015〜2018年の8つ（研究「複勝以外の回収率100超」の手順6 と同じ）と、同じ形（検証は直前の半年）で足した 2019〜2025年の14と、
#: 2026年（1〜10月）の1つ。学習は 2012年1月（表の始まり）から検証の始まりの前日まで。
HORSE_WINDOWS: tuple[TestWindow, ...] = (
    *OLDEST_WINDOWS,
    *(window for year in range(2019, 2026) for window in (
        TestWindow(f"{year}年前半", date(year - 1, 7, 1), date(year, 1, 1), date(year, 6, 30)),
        TestWindow(f"{year}年後半", date(year, 1, 1), date(year, 7, 1), date(year, 12, 31)),
    )),
    TestWindow("2026年", date(2025, 7, 1), date(2026, 1, 1), date(2026, 12, 31)),
)
