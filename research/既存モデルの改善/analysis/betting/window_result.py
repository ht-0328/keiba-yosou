"""1つの区切りの、買い方の検証の結果。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WindowResult:
    """1つの区切りの結果。

    - ``bought``: テスト期間に買った買い目（検証期間で回収率 100% 以上になった券種だけ）。
    - ``reference``: 参考。検証期間で選んだ買い方を、回収率が 100% に届かなくても買ったときの買い目（全券種）。
    - ``choices``: 券種ごとの、検証期間で選んだ買い方と、その検証期間の成績（1行 = 1券種）。
    - ``fit``: 勝率の出し方（材料の重みと Stern の補正）。
    """

    bought: pd.DataFrame
    reference: pd.DataFrame
    choices: list[dict[str, object]]
    fit: dict[str, object]
