"""組の表づくりのテスト（帯での絞り込みと、板が足りないときの動き）。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from ..dataset import DEFAULT_BANDS, DEFAULT_VALUE_LINE, ComboTableBuilder, PayoutBand
from . import synthetic_race as race

WIDE, QUINELLA, EXACTA = TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA
TRIO, TRIFECTA = TicketType.TRIO, TicketType.TRIFECTA


def test_既定の帯は5券種ぶんあり_期待値の線は1点05() -> None:
    lines = {band.ticket_type.label: (band.learn_from, band.high_line, band.cap) for band in DEFAULT_BANDS.values()}
    assert lines == {
        "ワイド": (3.0, 10.0, 300.0), "馬連": (8.0, 30.0, 1_000.0), "馬単": (15.0, 60.0, 3_000.0),
        "3連複": (20.0, 100.0, 3_000.0), "3連単": (100.0, 500.0, 10_000.0),
    }
    assert DEFAULT_VALUE_LINE == 1.05


def test_帯は_学ぶ下限以上で上限未満の組を対象にし_買うのは高配当の線以上() -> None:
    band = PayoutBand(QUINELLA, learn_from=8.0, high_line=30.0, cap=1_000.0)
    odds = pd.Series([7.9, 8.0, 29.9, 30.0, 999.9, 1_000.0])
    assert list(band.is_learnable(odds)) == [False, True, True, True, True, False]
    assert list(band.is_high_payout(odds)) == [False, False, False, True, True, False]


def test_帯の並びが逆なら作れない() -> None:
    with pytest.raises(ValueError, match="学ぶ下限"):
        PayoutBand(QUINELLA, learn_from=30.0, high_line=8.0, cap=1_000.0)


def test_対象の行は_オッズが学ぶ下限以上で上限未満の組だけ() -> None:
    # 馬単のオッズは 10 ＋ 3 × 1頭目 ＋ 2 × 2頭目。17倍以上・22倍未満の組だけが残る
    bands = {EXACTA: PayoutBand(EXACTA, learn_from=17.0, high_line=20.0, cap=22.0)}
    table = ComboTableBuilder(bands).build(race.horses(), race.boards())[EXACTA]
    expected = sorted(combo for combo in race.combos_of(EXACTA) if 17.0 <= race.odds_of(EXACTA, combo) < 22.0)
    assert sorted(zip(table["h1"], table["h2"])) == expected and len(expected) < len(race.combos_of(EXACTA))


def test_帯の中に組が無ければ_列だけの空の表() -> None:
    bands = {QUINELLA: PayoutBand(QUINELLA, learn_from=500.0, high_line=600.0, cap=700.0)}
    table = ComboTableBuilder(bands).build(race.horses(), race.boards())[QUINELLA]
    assert table.empty and "log_q" in table.columns and "baseline" in table.columns


def test_表を作る券種を絞れる() -> None:
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), race.boards(), [TRIO])
    assert list(tables) == [TRIO]


def test_3連単の板が無ければ_どの券種も作らない() -> None:
    boards = race.boards()
    del boards[TRIFECTA]
    assert ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards) == {}


def test_板が空の券種は_板が無いのと同じに扱う() -> None:
    boards = race.boards()
    boards[TRIFECTA] = boards[TRIFECTA].iloc[0:0]
    assert ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards) == {}


def test_馬単の板が無ければ_馬単とその板が要る材料を持つ券種を作らない() -> None:
    boards = race.boards()
    del boards[EXACTA]
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards)
    assert list(tables) == [TRIO]   # 3連複の材料はワイドと馬連の板だけを使う


def test_3連複の板が無ければ_3連複と3連単だけを作らない() -> None:
    boards = race.boards()
    del boards[TRIO]
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards)
    assert list(tables) == [WIDE, QUINELLA, EXACTA]


def test_馬ごとの表に無い馬を含む組は落とす() -> None:
    numbers = (1, 2, 3, 4, 5)   # 5番は板にだけいて、馬ごとの表にいない
    boards = {ticket_type: race.board(ticket_type, numbers=numbers) for ticket_type in race.ALL_TICKET_TYPES}
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards)
    assert len(tables[QUINELLA]) == 6 and set(tables[QUINELLA]["h2"]) <= {2, 3, 4}
    assert len(tables[TRIFECTA]) == 24 and not (tables[TRIFECTA][["h1", "h2", "h3"]] == 5).any().any()


def test_馬ごとの表に無いレースの板は使わない() -> None:
    other_race = "2025010506010102"
    boards = {
        ticket_type: pd.concat([race.board(ticket_type), race.board(ticket_type, other_race)], ignore_index=True)
        for ticket_type in race.ALL_TICKET_TYPES
    }
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards)
    assert set(tables[WIDE]["race_id"]) == {race.RACE} and len(tables[WIDE]) == 6


def test_何レースぶんでも_レースごとに材料を作る() -> None:
    other_race = "2025010506010102"
    horses = pd.concat([race.horses(), race.horses(other_race)], ignore_index=True)
    boards = {
        ticket_type: pd.concat([race.board(ticket_type), race.board(ticket_type, other_race)], ignore_index=True)
        for ticket_type in race.ALL_TICKET_TYPES
    }
    both = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(horses, boards)[TRIO]
    alone = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), race.boards())[TRIO]
    first = both[both["race_id"] == race.RACE].reset_index(drop=True)
    assert len(both) == 8
    pd.testing.assert_frame_equal(first, alone.reset_index(drop=True))
