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


def _with_danger(table: pd.DataFrame, dangers: dict[int, bool]) -> pd.DataFrame:
    """人気馬の危険の判定の列を足す（判定の無い馬は欠損値）。"""
    flags = table["horse_no"].map(dangers)
    return table.assign(is_danger=flags, out_probability=flags.map({True: 0.5, False: 0.3}),
                        market_out=flags.map({True: 0.35, False: 0.3}), danger_score=flags.map({True: 0.15, False: 0.0}),
                        danger_line=flags.map({True: 0.11, False: 0.11}))


def test_危険な人気馬は消にして残りの馬に二重丸から付ける() -> None:
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.1]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 30.0, 40.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.1, 0.05]
    values = [0.9] * 8
    race = _with_danger(_race(probabilities, odds, market, values), {1: True, 2: False, 3: False})
    marked = MarkRule().assign(race).set_index("horse_no")
    assert marked.loc[1, MARK] == OUT_MARK and "危険な人気馬" in marked.loc[1, "mark_reason"]
    assert [marked.loc[no, MARK] for no in range(2, 8)] == ["◎", "○", "▲", "△", "△", "△"]
    assert "全頭ではレース内2位" in marked.loc[2, "mark_reason"]
    assert marked.loc[8, MARK] in (OUT_MARK, "注")


def test_危険な人気馬には星も注も付けない() -> None:
    # 9頭立て。危険と判定された馬が、印の無い馬の中で上げ下げが最大でも 注 にしない
    probabilities = [0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
    odds = [2.0, 3.0, 4.0, 5.0, 8.0, 9.0, 10.0, 12.0, 15.0]
    market = [0.7, 0.55, 0.45, 0.3, 0.3, 0.3, 0.25, 0.2, 0.15]
    values = [0.9] * 9
    race = _with_danger(_race(probabilities, odds, market, values), {1: True})
    marked = MarkRule().assign(race)
    assert marked.set_index("horse_no").loc[1, MARK] == OUT_MARK
    assert marked[MARK].tolist().count("◎") == 1
