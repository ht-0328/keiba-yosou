"""過去で学習して次の期間を予想する検証（ウォークフォワード）の、期間の区切り（既存モデルの修正計画の 3）。

| 名前 | 仕事 |
|---|---|
| ``TestWindow`` | 1つの検証の区切り（学習・検証・テストの期間）。学習データを3つに分ける |
| ``WINDOWS`` | 2023年前半〜2026年の7つの区切り |
| ``DATA_FIRST_DAY`` | 学習に使う最初の開催日（2017年1月1日。学習データの表の始まり） |
| ``STAKES_WINDOWS`` | 重賞の予想の、2020年〜2026年の1年ずつの7つの区切り（重賞はレースが少ないので1年ずつ） |
| ``windows_of`` | 予想の名前から、その予想の区切りの並びを引く |
"""

from .test_window import TestWindow
from .stakes_windows import STAKES_DATA_FIRST_DAY, STAKES_WINDOWS
from .test_windows import DATA_FIRST_DAY, WINDOWS, window_named
from .window_catalog import windows_of

__all__ = ["TestWindow", "WINDOWS", "DATA_FIRST_DAY", "window_named", "STAKES_WINDOWS", "STAKES_DATA_FIRST_DAY", "windows_of"]
