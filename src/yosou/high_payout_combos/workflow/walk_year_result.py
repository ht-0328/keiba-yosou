"""年ごとの学習と予測の、1つの券種・1年ぶんの結果。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class WalkYearResult:
    """``WalkForwardWorkflow`` が、テストの年1つについて返す結果。

    - ``year``: テストの年（予測した年）。
    - ``train_row_count``・``valid_row_count``: 学習と検証（早期終了）に使った行の数（外れを間引いた後）。
    - ``tree_counts``: モデルの名前（LightGBM・CatBoost）→ 早期終了で残った木の数。
    - ``predicted_row_count``: 予測した行の数（その年の対象の組の全部）。``path``: 予測を書いたファイル。
    - ``was_skipped``: 前に作った予測があって、学び直さなかったか（そのときの行の数は 0、木の数は空）。
    """

    ticket_type: TicketType
    year: int
    train_row_count: int
    valid_row_count: int
    tree_counts: dict[str, int]
    predicted_row_count: int
    path: Path
    was_skipped: bool = False
