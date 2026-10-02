"""3回目の検証の段階（探索・確認・最後の1回）。"""

from __future__ import annotations

from enum import Enum

from .protocol import CONFIRM_WINDOW_NAMES, FINAL_WINDOW_NAMES, SEARCH_WINDOW_NAMES


class Stage(Enum):
    """入口 ``backtest_round3.py --stage`` の段階。値はコマンドで書く名前。

    段階ごとに、評価する区切りと、結果を置くフォルダ（``reports/馬券の買い方の検証/round3/<folder>``）が決まる。
    確認と最後の1回は、明示したときだけ動く（docs/05-round3-protocol.md）。
    """

    SEARCH = "search"
    CONFIRM = "confirm"
    FINAL = "final"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return _LABELS[self]

    @property
    def window_names(self) -> tuple[str, ...]:
        """この段階で評価する区切り。"""
        return _WINDOWS[self]

    @property
    def folder(self) -> str:
        """結果を置くフォルダの名前。"""
        return self.value

    @property
    def runs_once(self) -> bool:
        """1回だけの約束の段階か（出力が既にあれば動かない）。"""
        return self is not Stage.SEARCH


_LABELS: dict[Stage, str] = {Stage.SEARCH: "探索", Stage.CONFIRM: "確認", Stage.FINAL: "最後の1回"}
_WINDOWS: dict[Stage, tuple[str, ...]] = {
    Stage.SEARCH: SEARCH_WINDOW_NAMES, Stage.CONFIRM: CONFIRM_WINDOW_NAMES, Stage.FINAL: FINAL_WINDOW_NAMES,
}
