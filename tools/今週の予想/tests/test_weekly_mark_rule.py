"""MarkRule（全頭に ◎○▲△☆注消 を付ける）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import MARK, PROBABILITY, RANK
from 今週の予想.mark_rule import MarkRule, OUT_MARK


def _race(probabilities, odds=None, market=None, values=None) -> pd.DataFrame:
    size = len(probabilities)
    table = pd.DataFrame({"horse_no": range(1, size + 1), "horse_name": [f"馬{i}" for i in range(1, size + 1)],
                          PROBABILITY: probabilities})
    if odds is not None:
        table = table.assign(win_odds=odds, market_top3=market, place_value=values)
    return table


def test_木曜は確率の順に6頭へ印を付け残りは消() -> None:
    marked = MarkRule().assign(_race([0.1, 0.5, 0.3, 0.2, 0.4, 0.05, 0.15, 0.02]))
    assert marked["horse_no"].tolist() == [2, 5, 3, 4, 7, 1, 6, 8]
    assert marked[MARK].tolist() == ["◎", "○", "▲", "△", "△", "△", OUT_MARK, OUT_MARK]
    assert marked[RANK].tolist() == [1, 2, 3, 4, 5, 6, 7, 8]


def test_穴馬で複勝の期待値が線以上なら星を付ける() -> None:
    # 9頭立て: 人気馬は1〜3番人気。7位の馬（8番人気・期待値 1.4）に ☆
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.1, 0.05]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 30.0, 20.0, 40.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.1, 0.15, 0.05]
    values = [0.9, 0.9, 0.9, 1.3, 1.0, 1.0, 1.4, 0.8, 0.9]
    marked = MarkRule().assign(_race(probabilities, odds, market, values)).set_index("horse_no")
    assert marked.loc[7, MARK] == "☆"
    assert marked.loc[4, MARK] == "△"  # ◎〜△ の馬には ☆ を付けない


def test_星は線より下なら付けない() -> None:
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 30.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.25]
    values = [0.9, 0.9, 0.9, 1.0, 1.0, 1.0, 1.2]
    marked = MarkRule().assign(_race(probabilities, odds, market, values))
    assert "☆" not in marked[MARK].tolist()


def test_注は市場より来ると見る度合いが最大の馬() -> None:
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 10.0, 12.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.25, 0.05]
    values = [0.9, 0.9, 0.9, 1.0, 1.0, 1.0, 0.8, 1.1]
    marked = MarkRule().assign(_race(probabilities, odds, market, values)).set_index("horse_no")
    assert marked.loc[8, MARK] == "注"
    assert marked.loc[7, MARK] == OUT_MARK


def test_注は市場より低く見ている馬には付けない() -> None:
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.1]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 10.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.2]
    values = [0.9, 0.9, 0.9, 1.0, 1.0, 1.0, np.nan]
    marked = MarkRule().assign(_race(probabilities, odds, market, values))
    assert marked[MARK].tolist()[-1] == OUT_MARK
    assert all(reason for reason in marked["mark_reason"])
