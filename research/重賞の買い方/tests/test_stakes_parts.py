"""研究「重賞の買い方」の部品のテスト。値は架空。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 全レース全券種の買い方.analysis.cell_selector import CellChoice  # noqa: E402
from 全レース全券種の買い方.analysis.day_table import HIT_RACES, PAYOUT, POINTS, RACES  # noqa: E402
from 重賞の買い方.analysis import RANKS, GradedCells, PlaceBaseline, WinningTickets  # noqa: E402

DAYS = [pd.Timestamp("2025-01-05"), pd.Timestamp("2025-01-06")]


def _grades() -> pd.DataFrame:
    return pd.DataFrame({"race_id": ["r1", "r2", "r3", "r4"], "race_date": DAYS + DAYS, "rank": ["S", "B", "－", "A"],
                         "cell": ["S/A", "B/C", "－/－", "A/B"]})


def test_graded_cells_keeps_only_graded_races_and_uses_rank_as_cell():
    table = GradedCells().build(_grades(), pd.DataFrame({"race_id": ["r1", "r3", "r4"]}))
    # r2 は重賞でない、r3 は ◎ランクが無いので落ちる
    assert table["race_id"].tolist() == ["r1", "r4"]
    assert table["cell"].tolist() == ["S", "A"]


def _choice(cell: str, recovery: float, lower: float) -> CellChoice:
    return CellChoice(cell, 0, "型", recovery, lower, 20, 100, 3.0, True)


def test_winning_tickets_takes_tickets_over_100_or_best_lower():
    choices = {
        "単勝": [_choice("S", 1.10, 0.9), _choice("A", 0.80, 0.5)],
        "馬連": [_choice("S", 0.95, 0.8), _choice("A", 0.90, 0.7)],
        "3連単": [_choice("S", 1.30, 0.6), _choice("A", 0.85, np.nan)],
    }
    chosen = WinningTickets().choose(choices, ["単勝", "馬連", "3連単"], ["S", "A"])
    assert chosen["S"] == ["単勝", "3連単"]
    # 100% 以上が無いセルは、下の端がいちばん高い券種を1つ（欠損値は選ばない）
    assert chosen["A"] == ["馬連"]


def test_place_baseline_buys_top_two_place_values_without_danger():
    marked = pd.DataFrame({
        "race_id": ["r1"] * 4 + ["r4"] * 3,
        "mark": ["◎", "消", "○", "▲", "◎", "○", "▲"],
        "place_value": [1.2, 1.5, 0.9, 0.7, 0.8, 1.1, 0.6],
        "place_payout": [0.0, 300.0, 180.0, 400.0, 150.0, 0.0, 0.0],
    })
    cells_table = pd.DataFrame({"race_id": ["r1", "r4"], "race_date": DAYS, "cell": ["S", "A"]})
    values = PlaceBaseline().build(marked, cells_table, list(RANKS), DAYS)
    # r1: 消を除いて ◎(1.2)・○(0.9) を買う → 2点・払戻 180・当たり 1
    assert values[0, 0, POINTS] == 2 and values[0, 0, PAYOUT] == 180.0 and values[0, 0, RACES] == 1 and values[0, 0, HIT_RACES] == 1
    # r4: ○(1.1)・◎(0.8) を買う → 2点・払戻 150
    assert values[1, 1, POINTS] == 2 and values[1, 1, PAYOUT] == 150.0
    assert values[2:].sum() == 0


def test_ticket_chooser_picks_best_lower_among_tickets_with_enough_hits():
    from 重賞の買い方.analysis import TicketChooser
    def choice(cell, lower, enough):
        return CellChoice(cell, 0, "型", 1.0, lower, 30 if enough else 5, 100, 1.0, enough)
    choices = {
        "単勝": [choice("S/A", 0.95, True), choice("B/B", 0.70, False)],
        "3連単": [choice("S/A", 1.20, False), choice("B/B", 0.60, False)],
        "ワイド": [choice("S/A", 1.05, True), choice("B/B", np.nan, False)],
    }
    chosen = TicketChooser().choose(choices, ["S/A", "B/B"])
    # S/A: 当たりが足りる券種（単勝・ワイド）の中で下の端がいちばん高いワイド（足りない 3連単は高くても選ばない）
    assert chosen[0].ticket == "ワイド"
    # B/B: 足りる券種が無いので全券種から下の端がいちばん高い単勝（欠損値は選ばない）
    assert chosen[1].ticket == "単勝"


def test_single_rule_picks_place_horses_by_value_popularity_odds_and_field():
    from 重賞の買い方.analysis.single_ticket_grid import SingleRule, SingleTicketGrid
    horses = pd.DataFrame({
        "race_id": ["r1"] * 4 + ["r2"], "race_date": [DAYS[0]] * 4 + [DAYS[1]], "popularity": [2, 4, 5, 6, 5], "field_size": [14] * 4 + [10],
        "place_value": [1.2, 1.1, 1.02, 1.3, 1.2], "place_odds_low": [1.5, 2.5, 3.0, 6.0, 2.0], "place_payout": [150, 260, 0, 0, 210],
        "win_value": [1.0] * 5, "win_odds": [3.0] * 5, "win_payout": [0] * 5})
    rule = SingleRule("複勝", 1.05, 4, 5.0, 12)
    # 2番人気（人気）・期待値 1.02（線）・複勝 6.0倍（オッズ）・10頭のレース（頭数）は外れ、残るのは r1 の 4番人気の1頭
    assert list(horses[rule.chosen(horses)]["place_payout"]) == [260]
    score = SingleTicketGrid().score(horses, rule)
    assert score["点"] == 1 and score["当たり"] == 1 and abs(score["回収率"] - 2.6) < 1e-9
    assert rule.label == "複勝: 期待値 1.05 以上・4番人気以下・オッズ 5倍以下・12頭以上"


def test_race_logit_probabilities_sum_to_one_in_each_race_and_learn_the_winning_side():
    from 重賞の買い方.analysis.race_logit import RaceLogit
    # 2レース × 3組。どちらのレースも、もとの値が大きい組が当たる
    table = pd.DataFrame({"race_id": ["r1"] * 3 + ["r2"] * 3, "y": [2015] * 6, "hit": [1, 0, 0, 1, 0, 0],
                          "f1": [1.0, 0.0, -1.0, 2.0, 0.5, 0.0]})
    weights = RaceLogit().fit(table, ["f1"])
    probability = RaceLogit().probability(table, table[["f1"]].to_numpy() @ weights)
    assert weights[0] > 1.0
    assert abs(probability[:3].sum() - 1.0) < 1e-9 and abs(probability[3:].sum() - 1.0) < 1e-9 and probability[0] > probability[1]
