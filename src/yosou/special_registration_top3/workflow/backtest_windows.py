"""7つの区切りでの確かめの、区切りの表（設計書 16 の 4）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from yosou.shared.dataset import TrainingPeriod


@dataclass(frozen=True)
class BacktestWindow:
    """過去で学習して次の半年を予想する確かめの、1つの区切り。

    - ``name``: 区切りの名前（予測の表の「区切り」の列にも書く）。
    - ``valid_first_day``・``test_first_day``: 検証データ・テストデータの始まり。
    - ``end``: テスト期間の終わり（この日を含まない）。None は DB にある最後の日まで。
    """

    name: str
    valid_first_day: date
    test_first_day: date
    end: date | None

    def period(self, warmup_first_day: date, train_first_day: date) -> TrainingPeriod:
        """この区切りの学習データの期間（学習の始まりは区切りによらず同じ）。"""
        return TrainingPeriod(warmup_first_day, train_first_day, self.valid_first_day, self.test_first_day)


#: 中央の予想と同じ7つの半年の区切り（検証は直前の半年、テストはその次の半年）。
WINDOWS: tuple[BacktestWindow, ...] = (
    BacktestWindow("2023年前半", date(2022, 7, 1), date(2023, 1, 1), date(2023, 7, 1)),
    BacktestWindow("2023年後半", date(2023, 1, 1), date(2023, 7, 1), date(2024, 1, 1)),
    BacktestWindow("2024年前半", date(2023, 7, 1), date(2024, 1, 1), date(2024, 7, 1)),
    BacktestWindow("2024年後半", date(2024, 1, 1), date(2024, 7, 1), date(2025, 1, 1)),
    BacktestWindow("2025年前半", date(2024, 7, 1), date(2025, 1, 1), date(2025, 7, 1)),
    BacktestWindow("2025年後半", date(2025, 1, 1), date(2025, 7, 1), date(2026, 1, 1)),
    BacktestWindow("2026年", date(2025, 7, 1), date(2026, 1, 1), None),
)


def windows_named(names: Sequence[str] | None) -> tuple[BacktestWindow, ...]:
    """名前で選んだ区切り（並びは ``WINDOWS`` の順）。省略すると7つ全部。知らない名前なら ``ValueError``。"""
    if not names:
        return WINDOWS
    known = {window.name: window for window in WINDOWS}
    unknown = [name for name in names if name not in known]
    if unknown:
        raise ValueError(f"知らない区切りです: {unknown[0]}（{' / '.join(known)}）")
    return tuple(window for window in WINDOWS if window.name in set(names))
