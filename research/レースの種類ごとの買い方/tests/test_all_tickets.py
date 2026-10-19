"""手順6（全券種で回収率と的中率）の部品のテスト。値は架空で、DB は使わない。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from レースの種類ごとの買い方.analysis.bracket_features import BracketFeatures
from レースの種類ごとの買い方.analysis.buy_rule import BuyRule
from レースの種類ごとの買い方.analysis.cross_pool_features import CrossPoolFeatures
from レースの種類ごとの買い方.analysis.filter_selector import FilterSelector
from レースの種類ごとの買い方.analysis.hit_rate_selector import HitRateSelector
from レースの種類ごとの買い方.analysis.horse_bets import HorseBets
from レースの種類ごとの買い方.analysis.race_kinds import RaceKinds
from レースの種類ごとの買い方.analysis.rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES


def _kinds(race_id: str = "1") -> pd.DataFrame:
    return RaceKinds().label(pd.DataFrame({"race_id": [race_id], "race_date": ["2020-01-05"], "surface": ["芝"], "class_name": ["1勝クラス"],
                                           "field_size": [4], "weight_type": ["定量"]}))


def test_枠連は馬連の組を枠の組に足し合わせ_枠連のオッズで市場をそろえる() -> None:
    # 1枠に 1・2番、2枠に 3・4番。馬連の6組の q・t・hv を枠の組（1-1・1-2・2-2）に足す。
    pairs = [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]
    quinella = pd.DataFrame({"rid": [1] * 6, "h1": [a for a, _ in pairs], "h2": [b for _, b in pairs], "q": [0.1, 0.2, 0.2, 0.2, 0.2, 0.1],
                             "t": 1 / 6, "hv": 1 / 6, "race_date": pd.Timestamp("2020-01-05"), "expectation": "高", "fold": "2020年前半", "top": 3})
    frames = pd.DataFrame({"race_id": ["1"] * 4, "horse_no": [1, 2, 3, 4], "frame": [1, 1, 2, 2]})
    odds = pd.DataFrame({"race_id": ["1"] * 3, "combo": ["11", "12", "22"], "odds": [10.0, 2.0, 10.0]})
    payouts = pd.DataFrame({"race_id": ["1"], "combo": ["12"], "payout": [200.0]})
    table = BracketFeatures().build(quinella, frames, odds, payouts, _kinds()).set_index("combo")
    assert np.exp(table.loc["12", "log_quinella"]) == pytest.approx(0.8)            # 1-3・1-4・2-3・2-4 の和
    assert np.exp(table.loc["11", "log_quinella"]) == pytest.approx(0.1)            # 同じ枠どうし（1-2）
    assert np.exp(table["log_own"]).sum() == pytest.approx(1.0) and table.loc["12", "hit"] and table.loc["12", "top"] == 2


def test_単勝の候補は期待値とオッズで絞り_本命の馬番を写す() -> None:
    marked = pd.DataFrame({"race_id": [1, 1, 1], "race_date": ["2020-01-05"] * 3, "fold": "2020年前半", "expectation": "高",
                           "horse_no": [1, 2, 3], "mark": ["◎", "○", ""], "win_value": [1.1, 0.9, 1.3], "win_odds": [3.0, 5.0, 80.0],
                           "win_payout": [300.0, 0.0, 0.0]})
    table = HorseBets().of(TicketType.WIN, marked, _kinds())
    assert table["h1"].tolist() == [1] and table["top"].tolist() == [1] and table["hit"].tolist() == [True]   # 0.9 は線の下、80倍は上限の外


def _cross_folder(tmp_path: Path) -> Path:
    pd.DataFrame({"rid": [1, 1, 1], "h1": [1, 1, 2], "h2": [2, 3, 3], "q": [0.5, 0.3, 0.2]}).to_parquet(tmp_path / "quinella_2020.parquet")
    pd.DataFrame({"rid": [1, 1, 1], "h1": [1, 1, 2], "h2": [2, 3, 3], "q": [1.2, 1.0, 0.8]}).to_parquet(tmp_path / "wide_2020.parquet")
    pd.DataFrame({"rid": [1], "h1": [1], "h2": [2], "h3": [3], "q": [1.0]}).to_parquet(tmp_path / "trio_2020.parquet")
    return tmp_path


def test_ほかの券種の市場は2頭の対で引き_馬単は着順を区別しない(tmp_path: Path) -> None:
    cross = CrossPoolFeatures(_cross_folder(tmp_path))
    exacta = cross.add(TicketType.EXACTA, pd.DataFrame({"race_id": ["1"], "h1": [3], "h2": [1]}), 2020)
    assert np.exp(exacta.loc[0, "log_quinella_market"]) == pytest.approx(0.3) and np.exp(exacta.loc[0, "log_wide_market"]) == pytest.approx(1.0)
    wide = cross.add(TicketType.WIDE, pd.DataFrame({"race_id": ["1"], "h1": [2], "h2": [3]}), 2020)
    assert np.exp(wide.loc[0, "log_trio_market"]) == pytest.approx(1.0)               # 1-2-3 の組が 2・3番を含む
    trio = cross.add(TicketType.TRIO, pd.DataFrame({"race_id": ["1"], "h1": [1], "h2": [2], "h3": [3]}), 2020)
    assert trio.loc[0, "log_wide_pairs"] == pytest.approx(np.log(1.2) + np.log(1.0) + np.log(0.8), rel=1e-5)


def _stack(days: pd.DatetimeIndex) -> np.ndarray:
    """中身1つ・帯2つ・決まり2つ。決まり0（上限 30倍）は帯1 で毎日 3倍が当たる。決まり1（上限 1,000倍）は帯0・帯1 で毎日 1.5倍が当たる。"""
    table = np.zeros((2, 2, len(days), 4))
    table[:, :, :, POINTS] = 1.0
    table[:, :, :, RACES] = 1.0
    table[0, 1, :, PAYOUT], table[0, 1, :, HIT_RACES] = 300.0, 1.0
    table[1, :, :, PAYOUT], table[1, :, :, HIT_RACES] = 150.0, 1.0
    return table


def test_的中率を上げる条件と_オッズの上限の条件で選ぶ() -> None:
    days = pd.DatetimeIndex([pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=at) for year in (2016, 2017, 2018) for at in range(30)])
    rules = [BuyRule("全", 1.0, 30, 0), BuyRule("全", 1.0, 1000, 0)]
    selector = FilterSelector({"favorite_odds": _stack(days)}, days, rules)
    hit_rate = HitRateSelector(selector, days, rules)
    pick, cells = hit_rate.pick((2016, 2017, 2018), base_hit_rate=0.5)
    assert pick.rule == rules[0] and pick.filter_text == "favorite_odds の帯 2 以上" and cells[:, PAYOUT].sum() == 300.0 * len(days)
    capped, _ = hit_rate.pick((2016, 2017, 2018), base_hit_rate=0.5, min_good_share=1.0, max_cap=30)
    assert capped.rule == rules[0]
    none, cells = hit_rate.pick((2016, 2017, 2018), base_hit_rate=0.95)                # 1.1倍の的中率に届く組み合わせが無い
    assert none.rule is None and cells is None


def test_名前に絞りの付いた表は_そのレースだけの候補も作る() -> None:
    days = pd.DatetimeIndex([pd.Timestamp("2016-01-01")])
    table = np.zeros((1, 2, 1, 4))
    selector = FilterSelector({"favorite_odds": table, "agreement:favorite_odds": table}, days, [BuyRule("全", 1.0, 30, 0)])
    assert "agreement だけ" in selector.filter_texts and "agreement:favorite_odds の帯 1 以下" in selector.filter_texts
