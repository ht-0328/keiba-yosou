"""評価できない馬（所属が招待で中央の過去走が無い馬）の扱いと、買い方の名前の見せ方のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import IS_DANGER, MARK, PROBABILITY, UNRATED, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import NO_MARK, MarkRule
from 今週の予想.mark_tickets import MarkTickets
from 今週の予想.ticket_rules import PLACE_LABEL
from yosou.shared.win_value import HIGH
from 今週の予想.shown_rule_name import ShownRuleName
from 今週の予想.unrated_combos import COLUMN, UnratedCombos
from 今週の予想.unrated_horse import REASON, UnratedHorse


def test_招待で中央の過去走が無い馬だけを評価できない馬にする() -> None:
    affiliation = pd.Series(["招待", "招待", "美浦", "栗東", "招待"])
    runs = pd.Series([0, 3, 0, None, None])
    # 1番目（招待・0走）と 5番目（招待・出走数なし）だけ。中央で走った招待馬と、初出走の中央の馬は入らない
    assert UnratedHorse().of(affiliation, runs).tolist() == [True, False, False, False, True]


def _race(unrated: list[bool]) -> pd.DataFrame:
    """8頭。1番は単勝の期待値が1位（1.30）で、複勝の期待値も・市場との差もいちばん大きい。"""
    probabilities = [0.40, 0.45, 0.42, 0.35, 0.30, 0.25, 0.20, 0.15]
    odds = [6.0, 3.0, 4.0, 5.0, 8.0, 12.0, 20.0, 40.0]
    wins = [0.22, 0.25, 0.20, 0.12, 0.09, 0.06, 0.04, 0.02]
    table = pd.DataFrame({"horse_no": range(1, 9), "horse_name": [f"馬{i}" for i in range(1, 9)], PROBABILITY: probabilities,
                          "win_odds": odds, "market_top3": [0.30, 0.55, 0.45, 0.40, 0.30, 0.22, 0.15, 0.08],
                          "place_value": [1.40, 0.9, 0.9, 0.9, 0.9, 1.30, 0.9, 0.9], WIN_PROBABILITY: wins, UNRATED: unrated})
    table[WIN_VALUE] = table[WIN_PROBABILITY] * table["win_odds"]
    return table


def test_評価できない馬はどの印の候補にもせず無印にして理由を書く() -> None:
    before = MarkRule().assign(_race([False] * 8)).set_index("horse_no")
    assert before.loc[1, MARK] == "◎"
    after = MarkRule().assign(_race([True] + [False] * 7).assign(**{IS_DANGER: [True] + [False] * 7})).set_index("horse_no")
    # 1番は ◎ にも消にもならず、無印で理由が付く。◎ は残りの馬の中で単勝の期待値が1位の馬に移る
    assert after.loc[1, MARK] == NO_MARK and after.loc[1, "mark_reason"] == REASON
    assert (after[MARK] == "◎").sum() == 1 and after.loc[1, MARK] != "消"


def _places(unrated: list[bool]) -> set[str]:
    race = MarkRule().assign(_race(unrated))
    race = race.assign(race_id="R", race_date=pd.Timestamp("2026-01-01"), fold="", win_value_band=HIGH, field_size=16,
                       place_odds_low=2.0, place_odds_high=3.0)
    tickets = MarkTickets().build(race)
    return set(tickets.loc[tickets["rule"] == PLACE_LABEL, "combo"])


def test_評価できない馬は印で選ばない買い目にも入れない() -> None:
    # 6番（複勝の期待値 1.30）は、評価できる馬なら複勝の買い目に入り、評価できない馬なら入らない
    assert "06" in _places([False] * 8)
    assert "06" not in _places([False] * 5 + [True] + [False] * 2)


def test_組の期待値の買い目から評価できない馬を含む組を外す() -> None:
    races = UnratedCombos().attach(pd.DataFrame({"race_id": ["A", "B"]}),
                                   pd.DataFrame({"race_id": ["A", "A", "B"], "horse_no": [1, 2, 3], UNRATED: [True, False, False]}))
    assert races[COLUMN].tolist() == [frozenset({1}), frozenset()]
    chosen = pd.DataFrame({"race_id": ["A", "A", "B"], "h1": [2, 3, 1], "h2": [1, 4, 2]}).merge(races, on="race_id")
    # レース A の 1番を含む組だけ。レース B の 1番は評価できる馬
    assert UnratedCombos().hits(chosen, ("h1", "h2")).tolist() == [True, False, False]


def test_星を相手に入れなかったレースは買い方の名前から星を除いて理由を添える() -> None:
    horses = [{"horse_no": 12, "mark": "☆", "place_value": 0.85}, {"horse_no": 1, "mark": "◎", "place_value": 1.1}]
    shown = ShownRuleName(horses)
    assert shown.of("3連単（◎→○▲☆→○▲△☆）") == "3連単（◎→○▲→○▲△）"
    assert shown.note() is not None and "☆ 12" in shown.note() and "0.85" in shown.note()
    used = ShownRuleName([{"horse_no": 12, "mark": "☆", "place_value": 1.30}])
    assert used.of("3連単（◎→○▲☆→○▲△☆）") == "3連単（◎→○▲☆→○▲△☆）" and used.note() is None
    # 全頭の分からない予想（前の形）は名前をそのまま
    assert ShownRuleName(None).of("馬連") == "馬連"
