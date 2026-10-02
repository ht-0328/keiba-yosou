"""1つの区切りの、買い方の検証の結果。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class WindowResult:
    """1つの区切りの結果。

    - ``bought``: テスト期間に買った買い目。
    - ``reference``: 参考。検証期間で線を決めた券種を、回収率が 100% に届かなくても買ったときの買い目。
    - ``choices``: 券種ごとの、検証期間で選んだ線と、その検証期間の成績（1行 = 1券種）。
    - ``fit``: 勝率の出し方（材料の重みと Stern の補正）と、選んだレース数・消・2頭軸・荒れそうの線。
    - ``candidates``・``races``: テスト期間の全部の買い目の候補（確率を補正したもの。期待値のカットの前）とレース単位の表
      （確率のずれの表に使う）。
    - ``valid_candidates``・``valid_tickets``・``valid_races``: この区切りの検証の半年の、補正する前の候補・買い目の組・レース単位の表。
      次の区切りの検証期間（1年）の前半に使う。
    - ``selections``・``selection_bought``: 勝負するレースの選び方の決まりごとの記録と、テスト期間に買った買い目
      （``SelectionRuleComparison`` の結果。決まりを渡さなければ空）。
    """

    bought: pd.DataFrame
    reference: pd.DataFrame
    choices: list[dict[str, object]]
    fit: dict[str, object]
    candidates: pd.DataFrame
    races: pd.DataFrame
    valid_candidates: pd.DataFrame
    valid_tickets: pd.DataFrame
    valid_races: pd.DataFrame
    selections: list[dict[str, object]] = field(default_factory=list)
    selection_bought: pd.DataFrame = field(default_factory=pd.DataFrame)
