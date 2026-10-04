"""DangerPicker（1レースで消にする危険な人気馬を1頭選ぶ）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.danger_picker import DangerPicker


def _pick(bands, dangers, lines, picker=None) -> list[bool]:
    return (picker or DangerPicker()).pick(pd.Series(bands), pd.Series(dangers), pd.Series(lines)).tolist()


def test_1番人気が線以上なら1番人気だけを消にする() -> None:
    # 2番人気のほうが線を大きく超えていても、1番人気を優先する
    assert _pick(["1番人気", "2〜3番人気", "2〜3番人気"], [0.12, 0.20, 0.0], [0.11, 0.05, 0.05]) == [True, False, False]


def test_1番人気が線未満なら2から5番人気で線をいちばん大きく超えた馬を消にする() -> None:
    # 2番人気は線を 0.02、4番人気は 0.03 超える。人気帯で線が違うので、危険度そのもの（0.08 と 0.05）ではなく線との差で比べる
    bands = ["1番人気", "2〜3番人気", "2〜3番人気", "4〜5番人気", "4〜5番人気"]
    assert _pick(bands, [0.05, 0.08, 0.01, 0.05, 0.0], [0.11, 0.06, 0.06, 0.02, 0.02]) == [False, False, False, True, False]


def test_線以上の馬がいないか線が無ければ消にしない() -> None:
    assert _pick(["1番人気", "2〜3番人気"], [0.05, 0.01], [0.11, 0.06]) == [False, False]
    assert _pick(["1番人気", "2〜3番人気"], [0.30, 0.30], [np.nan, np.nan]) == [False, False]


def test_消にできる人気帯を1番人気だけにすると2から5番人気は消にしない() -> None:
    assert _pick(["1番人気", "2〜3番人気"], [0.05, 0.20], [0.11, 0.06], DangerPicker(("1番人気",))) == [False, False]
