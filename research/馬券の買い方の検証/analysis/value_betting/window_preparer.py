"""区切りごとに、期待値・消・印を付けた材料を用意する（戦略に依らない部分）。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 既存モデルの改善.analysis.windows import WINDOWS, TestWindow, window_named

from . import columns as c
from .danger_exclusion import DangerExclusion
from .mark_assigner import MarkAssigner
from .materials import Round3Materials
from .place_price_fitter import PlacePriceFitter
from .place_value_calculator import PlaceValueCalculator
from .prepared_window import PreparedWindow


class WindowPreparer:
    """1つの区切りについて、見込みの倍率を学び（``PlacePriceFitter``）、テスト期間と直前の1年の行に複勝の期待値を付け
    （``PlaceValueCalculator``）、直前の1年で消の線を決めて付け（``DangerExclusion``）、テスト期間に印を付ける（``MarkAssigner``）。

    直前の1年 = 1つ前の区切りの検証の半年 ＋ この区切りの検証の半年。1つ前の区切りが材料に無ければ半年だけ。
    テスト期間の行は、どの線を決めるのにも使わない。同じ区切りを2回頼まれたら、1回目の結果を返す。
    """

    def __init__(self, materials: Round3Materials, windows: Sequence[TestWindow] = WINDOWS) -> None:
        self._materials = materials
        self._windows = tuple(windows)
        self._fitter = PlacePriceFitter(materials.price_history)
        self._prepared: dict[str, PreparedWindow] = {}

    def prepare(self, name: str) -> PreparedWindow:
        if name not in self._prepared:
            self._prepared[name] = self._build(window_named(name, self._windows))
        return self._prepared[name]

    def _build(self, window: TestWindow) -> PreparedWindow:
        calculator = PlaceValueCalculator(self._fitter.for_window(window))
        previous = self._previous_valid(window)
        history = pd.concat([previous, self._materials.runners_of(window.name, c.PART_VALID)], ignore_index=True)
        valued_history = calculator.add(history)
        exclusion = DangerExclusion().fit(valued_history)
        test = MarkAssigner().assign(exclusion.mark(calculator.add(self._materials.runners_of(window.name, c.PART_TEST))))
        return PreparedWindow(window.name, test.reset_index(drop=True), exclusion.mark(valued_history),
                              self._materials.races_of(window.name, c.PART_TEST).reset_index(drop=True),
                              history_is_full_year=not previous.empty, danger_lines=exclusion.lines)

    def _previous_valid(self, window: TestWindow) -> pd.DataFrame:
        """1つ前の区切りの検証の半年の行。1つ前が無いか材料に無ければ空。"""
        position = self._windows.index(window)
        if position == 0:
            return self._materials.runners.iloc[0:0]
        return self._materials.runners_of(self._windows[position - 1].name, c.PART_VALID)
