"""1つの区切りの、買い方の検証の結果。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WindowResult:
    """1つの区切りの結果。

    - ``bought``: テスト期間に買った買い目（検証期間で回収率 100% 以上になった券種の、期待値の線以上の買い目）。
    - ``reference``: 参考。検証期間で線を決めた券種を、回収率が 100% に届かなくても買ったときの買い目。
    - ``choices``: 券種ごとの、検証期間で選んだ線と、その検証期間の成績（1行 = 1券種）。
    - ``fit``: 勝率の出し方（材料の重みと Stern の補正）と、選んだ勝負するレース・押さえ・消の線。
    - ``candidates``・``races``: テスト期間の、印のルールで作った全部の買い目（カットの前）と、レース単位の表。
      次の区切りの検証期間（1年）の前半に使い、確率のずれの表にも使う。
    """

    bought: pd.DataFrame
    reference: pd.DataFrame
    choices: list[dict[str, object]]
    fit: dict[str, object]
    candidates: pd.DataFrame
    races: pd.DataFrame
