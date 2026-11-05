"""段5 の研究に残る部品（成績）を架空の値で確かめる。条件つきロジット・票の表・券種ごとの確率・買い方は本番の道具 tools/地方の推奨買目 に移し、テストもそちらにある。"""

from __future__ import annotations

import pandas as pd

from 地方の万馬券.analysis.positions.ticket_summary import TicketSummary
from 地方の推奨買目.position_model import PROBABILITY

_BASE_RACE = 2024010101010100


def test_成績の行は_回収率と的中と落ち込みを数える():
    races = pd.DataFrame({"race_id": [_BASE_RACE, _BASE_RACE + 1], "race_date": ["2024-01-01", "2024-01-02"]})
    chosen = pd.DataFrame({"race_id": [_BASE_RACE, _BASE_RACE, _BASE_RACE + 1], PROBABILITY: [0.2, 0.1, 0.3], "payout": [500, 0, 0]})
    row = TicketSummary().row("単勝", "全部・期待値 1 以上", "2024年", chosen, races)
    assert row["点数"] == 3 and row["投資"] == "300円" and row["払戻"] == "500円" and row["回収率"] == "166.7%"
    assert row["的中"] == 1 and row["的中率"] == "50.0%" and row["最大の落ち込み"] == "-100円"
    monthly = TicketSummary().monthly(chosen, races)
    assert list(monthly["月"]) == ["2024-01"] and monthly["損益"].iloc[0] == 200
