"""研究「レースの種類ごとの買い方」の部品のテスト。値は架空で、DB は使わない。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlendFitter

from レースの種類ごとの買い方.analysis.buy_rule import BuyRule, CURRENT_RULES, rules_of
from レースの種類ごとの買い方.analysis.combo_features import ComboFeatures
from レースの種類ごとの買い方.analysis.design_matrix import DesignMatrix
from レースの種類ごとの買い方.analysis.penalized_blend_fitter import PenalizedBlendFitter
from レースの種類ごとの買い方.analysis.race_kinds import KIND_DUMMIES, RaceKinds
from レースの種類ごとの買い方.analysis.rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES, RuleDayTable
from レースの種類ごとの買い方.analysis.walk_forward_report import WalkForwardReport
from レースの種類ごとの買い方.analysis.walk_forward_selector import BY_KIND, UNIFORM, WalkForwardSelector
from レースの種類ごとの買い方.analysis.weight_method import METHODS


def test_種類の印は芝ダ_クラス_頭数_ハンデから付ける() -> None:
    races = pd.DataFrame({"race_id": [1, 2], "race_date": ["2020-01-05", "2020-01-05"], "surface": ["ダート", "芝"],
                          "class_name": ["未勝利", "G3"], "field_size": [12, 9], "weight_type": ["馬齢", "ハンデ"]})
    kinds = RaceKinds().label(races).set_index("race_id")
    assert kinds.loc["1", "kind_group"] == "ダート・新馬・未勝利" and kinds.loc["2", "kind_group"] == "芝・上のクラス"
    assert kinds.loc["1", list(KIND_DUMMIES)].tolist() == [1.0, 1.0, 0.0, 0.0, 1.0, 0.0]
    assert kinds.loc["2", list(KIND_DUMMIES)].tolist() == [0.0, 0.0, 1.0, 1.0, 0.0, 1.0]


def test_材料は穴馬の比と_本命を含むかを付ける() -> None:
    raw = pd.DataFrame({"rid": [1, 1], "odds": [5.0, 50.0], "q": [0.2, 0.02], "t": [0.2, 0.02], "hv": [0.2, 0.02],
                        "payout": [500.0, 0.0], "race_date": ["2020-01-05"] * 2, "expectation": ["高"] * 2, "fold": ["2020年前半"] * 2,
                        "top": [3, 3], "h1": [3, 1], "h2": [1, 2], "pop1": [1, 12], "pop2": [12, 2],
                        "rt1": [1.0, 2.0], "rt2": [2.0, 1.0], "rw1": [1.5, 3.0]})
    kinds = RaceKinds().label(pd.DataFrame({"race_id": [1], "race_date": ["2020-01-05"], "surface": ["芝"], "class_name": ["1勝クラス"],
                                            "field_size": [16], "weight_type": ["定量"]}))
    table = ComboFeatures(".").build(TicketType.EXACTA, raw, kinds)
    assert table["hit"].tolist() == [True, False]
    assert table["has_top"].tolist() == [1.0, 0.0]                                       # 馬単は ◎（3番）が1着の組だけ
    assert table["log_ratio"].tolist() == pytest.approx([np.log(1.5) + np.log(2.0), np.log(3.0) + np.log(1.0)])   # 1頭目は1着の比
    assert table["longshot_ratio"].tolist() == pytest.approx([np.log(2.0), np.log(3.0)])  # 12番人気の馬の比だけ


def _synthetic(seed: int = 3) -> tuple[pd.DataFrame, np.ndarray]:
    """200レース × 6組。真の重みは もと a が 1.0・もと b が 0.5。"""
    rng = np.random.default_rng(seed)
    rows = []
    for race in range(200):
        a, b = rng.normal(size=6), rng.normal(size=6)
        p = np.exp(a + 0.5 * b)
        winner = rng.choice(6, p=p / p.sum())
        rows += [{"race_id": f"{race:04d}", "log_own": a[at], "log_trifecta": b[at], "log_harville": 0.0, "log_ratio": 0.0,
                  "hit": at == winner, **{name: float(race % 2 == 0 and name == "kind_dirt") for name in KIND_DUMMIES}}
                 for at in range(6)]
    frame = pd.DataFrame(rows)
    race = frame["race_id"].to_numpy()
    return frame, np.flatnonzero(np.r_[True, race[1:] != race[:-1]])


def test_罰則0で差の列が無ければ_本番の重みの推定と同じになる() -> None:
    frame, starts = _synthetic()
    design = DesignMatrix(METHODS[0])
    weights = PenalizedBlendFitter().fit(design.of(frame), frame["hit"].to_numpy(), starts, design.penalized())
    expected = ComboBlendFitter().fit(frame).values()
    assert weights == pytest.approx(np.asarray(expected), abs=1e-4)


def test_罰則を強くすると種類の差は0に近づく() -> None:
    frame, starts = _synthetic()
    design = DesignMatrix(METHODS[1])
    features, hit = design.of(frame), frame["hit"].to_numpy()
    loose = PenalizedBlendFitter(0.0).fit(features, hit, starts, design.penalized())
    tight = PenalizedBlendFitter(1e6).fit(features, hit, starts, design.penalized())
    assert np.abs(tight[design.penalized()]).max() < 1e-3 < np.abs(loose[design.penalized()]).max()
    assert features.shape[1] == 4 * (1 + len(KIND_DUMMIES))


def _valued() -> pd.DataFrame:
    """ワイドの組。r1 は 3組（オッズ 2・10・20倍。2倍が当たり）、r2 は 1組（30倍・外れ）。"""
    rows = [("r1", "2020-01-05", 2.0, 1.5, 200.0), ("r1", "2020-01-05", 10.0, 1.4, 0.0), ("r1", "2020-01-05", 20.0, 1.2, 0.0),
            ("r2", "2020-01-06", 30.0, 1.1, 0.0)]
    return pd.DataFrame([{"race_id": race, "race_date": date, "odds": odds, "value": value, "payout": payout, "hit": payout > 0,
                          "expectation": "高", "kind_group": "芝・1〜2勝", "top": 1, "h1": 1, "h2": 2} for race, date, odds, value, payout in rows])


def test_決まりごとに点数とトリガミを数える() -> None:
    days = pd.to_datetime(["2020-01-05", "2020-01-06"])
    rules = [BuyRule("全", 1.0, 300, 0), BuyRule("全", 1.3, 300, 0), BuyRule("全", 1.0, 300, 1), BuyRule("全", 1.0, 15, 0)]
    table = RuleDayTable(TicketType.WIDE, days).build(_valued(), rules)
    group = 1                                                       # 芝・1〜2勝
    everything = table[0, group]
    # r1 は3点で、2倍の組は 2 ≦ 3 なのでトリガミで外れ、残り2点（10倍 > 2）。r2 は1点。
    assert everything[:, POINTS].tolist() == [2.0, 1.0] and everything[:, PAYOUT].sum() == 0.0
    assert everything[:, RACES].tolist() == [1.0, 1.0]
    # 線 1.3 なら r1 の 2倍と 10倍の2点で、2倍は 2 ≦ 2 で外れ、10倍だけ残る。
    assert table[1, group, :, POINTS].tolist() == [1.0, 0.0]
    # 1点までなら期待値1位の 2倍の1点だけで、1点なら 2 > 1 なので残り、当たる。
    assert table[2, group, 0, POINTS] == 1.0 and table[2, group, 0, PAYOUT] == 200.0 and table[2, group, 0, HIT_RACES] == 1.0
    # 上限 15倍なら r1 の 2倍・10倍（2倍はトリガミ）。
    assert table[3, group, :, POINTS].tolist() == [1.0, 0.0]


def test_今の本番の決まりは候補に入っている() -> None:
    for ticket_type, rule in CURRENT_RULES.items():
        assert rule in rules_of(ticket_type)


def _table() -> tuple[np.ndarray, pd.DatetimeIndex]:
    """2つの決まり × 2つの種類 × 4年（各年 40日）。決まり0 は種類0 で毎日 +100円、種類1 で毎日 −100円。決まり1 は毎日 −50円。"""
    days = pd.DatetimeIndex([pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=at) for year in (2016, 2017, 2018, 2019) for at in range(40)])
    table = np.zeros((2, 2, len(days), 4))
    table[:, :, :, POINTS] = 1.0
    table[:, :, :, RACES] = 1.0
    table[0, 0, :, PAYOUT], table[0, 0, :, HIT_RACES] = 200.0, 1.0
    table[0, 1, :, PAYOUT] = 0.0
    table[1, :, :, PAYOUT] = 50.0
    table[1, :, ::2, HIT_RACES] = 1.0
    return table, days


def test_種類ごとに選び_利益の下の端が0以下の種類は買わない() -> None:
    table, days = _table()
    rules = [BuyRule("全", 1.0, 300, 0), BuyRule("全", 1.5, 300, 0)]
    daily, choices = WalkForwardSelector(table, days, rules, ["甲", "乙"]).run(BY_KIND, [2018, 2019])
    chosen = {(choice.year, choice.group): choice.rule for choice in choices}
    assert chosen[(2018, "甲")] == rules[0] and chosen[(2018, "乙")] is None
    in_2018 = days.year == 2018
    assert daily[in_2018, PAYOUT].sum() == 200.0 * 40 and daily[in_2018, POINTS].sum() == 40


def test_一律は種類を足した利益で選ぶ() -> None:
    table, days = _table()
    rules = [BuyRule("全", 1.0, 300, 0), BuyRule("全", 1.5, 300, 0)]
    _, choices = WalkForwardSelector(table, days, rules, ["甲", "乙"]).run(UNIFORM, [2018])
    assert choices[0].rule == rules[0]                              # 決まり0 の合計は ±0、決まり1 は −100円/日


def test_採用の基準は今の本番と比べて判定する() -> None:
    table, days = _table()
    report = WalkForwardReport(days)
    good = report.summary("良い案", table[0, 0])
    bad = report.summary("悪い案", table[1, 0])
    assert good.payback == pytest.approx(2.0) and bad.payback == pytest.approx(0.5)
    assert report.verdict(good, bad)[:3] == (True, True, True)
    assert report.verdict(bad, good)[0] is False
