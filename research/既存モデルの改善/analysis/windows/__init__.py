"""過去で学習して次の期間を予想する検証（ウォークフォワード）の、期間の区切り（既存モデルの修正計画の 3）。

| 名前 | 仕事 |
|---|---|
| ``TestWindow`` | 1つの検証の区切り（学習・検証・テストの期間）。学習データを3つに分ける |
| ``WINDOWS`` | 2023年前半〜2026年の7つの区切り |
| ``DATA_FIRST_DAY`` | 学習に使う最初の開催日（2017年1月1日。学習データの表の始まり） |
"""

from .test_window import TestWindow
from .test_windows import DATA_FIRST_DAY, WINDOWS, window_named

__all__ = ["TestWindow", "WINDOWS", "DATA_FIRST_DAY", "window_named"]
