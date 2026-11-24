"""本番のモデルの学習の、1つの券種ぶんの結果。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class ProductionTrainingResult:
    """``ProductionTraining`` が1つの券種について返す結果。

    - ``train_last_day``: 学習に使った最後の開催日。``valid_last_day``: 検証（早期終了）に使った最後の開催日（表のある最後の開催日）。
    - ``train_row_count``・``valid_row_count``: 学習と検証に使った行の数（外れを間引いた後）。
    - ``tree_counts``: モデルの名前（LightGBM・CatBoost）→ 早期終了で残った木の数。
    - ``losses``: 検証の行での対数損失（``MarketComparison.losses``。モデルごと・平均・市場）。
    - ``folder``: モデルを書いたフォルダ。
    """

    ticket_type: TicketType
    train_last_day: date
    valid_last_day: date
    train_row_count: int
    valid_row_count: int
    tree_counts: dict[str, int]
    losses: dict[str, float]
    folder: Path
