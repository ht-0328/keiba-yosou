"""契約: 3連単の確率の表から、券種ごとの買い目の当たる確率を、払戻の組番と同じ形で出す。

架空の6頭の1着の確率から Harville の式（設計書 03 の 5.）で3連単の表を作り、
単勝の確率が1着の確率と一致すること、各券種の確率の合計（馬連 1・ワイド 3・複勝 3 など）を確かめる。
"""

import itertools

import numpy as np
import pandas as pd
import pytest

from yosou.race_development.betting import TicketProbability
from yosou.race_development.betting.column_names import COMBO, FIRST, PROBABILITY, SECOND, THIRD
from yosou.shared.betting import TicketType

#: 架空の6頭立ての1着の確率（馬番 1〜6。合計 1）。
WIN = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}


def harville(win: dict[int, float], lam: float = 1.0) -> pd.DataFrame:
    """1着の確率から3連単の確率の表を作る（Harville の式に、ならしの指数 lam を付けたもの）。"""
    weight = {horse: probability ** lam for horse, probability in win.items()}
    total = sum(weight.values())
    rows = [
        (i, j, k, win[i] * weight[j] / (total - weight[i]) * weight[k] / (total - weight[i] - weight[j]))
        for i, j, k in itertools.permutations(win, 3)
    ]
    return pd.DataFrame(rows, columns=[FIRST, SECOND, THIRD, PROBABILITY])


@pytest.fixture
def trifecta() -> pd.DataFrame:
    return harville(WIN, lam=0.8)


def test_win_probability_is_the_first_place_probability(trifecta):
    win = TicketProbability().of(trifecta, TicketType.WIN, field_size=6)
    assert list(win[COMBO]) == ["01", "02", "03", "04", "05", "06"]
    assert np.allclose(win[PROBABILITY], list(WIN.values()))


@pytest.mark.parametrize(("ticket_type", "count", "total"), [
    (TicketType.WIN, 6, 1.0),
    (TicketType.QUINELLA, 15, 1.0),
    (TicketType.EXACTA, 30, 1.0),
    (TicketType.WIDE, 15, 3.0),
    (TicketType.TRIO, 20, 1.0),
    (TicketType.TRIFECTA, 120, 1.0),
])
def test_each_ticket_type_covers_every_combo_and_sums_right(trifecta, ticket_type, count, total):
    table = TicketProbability().of(trifecta, ticket_type, field_size=6)
    assert len(table) == count and table[COMBO].is_unique
    assert table[PROBABILITY].sum() == pytest.approx(total)


def test_place_is_top_two_up_to_seven_runners_and_top_three_from_eight():
    seven = TicketProbability().of(harville(WIN), TicketType.PLACE, field_size=7)
    assert seven[PROBABILITY].sum() == pytest.approx(2.0)
    eight_win = {horse: 1 / 8 for horse in range(1, 9)}
    eight = TicketProbability().of(harville(eight_win), TicketType.PLACE, field_size=8)
    assert eight[PROBABILITY].sum() == pytest.approx(3.0)
    assert np.allclose(eight[PROBABILITY], 3 / 8)


def test_combos_match_the_payout_table_format(trifecta):
    probability = TicketProbability()
    quinella = probability.of(trifecta, TicketType.QUINELLA, field_size=6)
    exacta = probability.of(trifecta, TicketType.EXACTA, field_size=6)
    trio = probability.of(trifecta, TicketType.TRIO, field_size=6)
    assert "0102" in set(quinella[COMBO]) and "0201" not in set(quinella[COMBO])
    assert {"0102", "0201"} <= set(exacta[COMBO])
    assert set(trio[COMBO]) == {"".join(f"{horse:02d}" for horse in trio_horses) for trio_horses in itertools.combinations(WIN, 3)}


def test_quinella_is_the_two_exactas_added(trifecta):
    probability = TicketProbability()
    quinella = probability.of(trifecta, TicketType.QUINELLA, field_size=6).set_index(COMBO)[PROBABILITY]
    exacta = probability.of(trifecta, TicketType.EXACTA, field_size=6).set_index(COMBO)[PROBABILITY]
    assert quinella["0305"] == pytest.approx(exacta["0305"] + exacta["0503"])


def test_wide_is_both_horses_in_the_top_three(trifecta):
    wide = TicketProbability().of(trifecta, TicketType.WIDE, field_size=6).set_index(COMBO)[PROBABILITY]
    in_top_three = trifecta[[FIRST, SECOND, THIRD]].isin([1, 2]).sum(axis=1) == 2
    assert wide["0102"] == pytest.approx(trifecta.loc[in_top_three, PROBABILITY].sum())


def test_eighteen_runners_are_fast_enough():
    win = {horse: 1 / 18 for horse in range(1, 19)}
    trifecta = harville(win)
    probability = TicketProbability()
    tables = [probability.of(trifecta, ticket_type, field_size=18) for ticket_type in TicketType]
    assert [len(table) for table in tables] == [18, 18, 153, 306, 153, 816, 4896]
