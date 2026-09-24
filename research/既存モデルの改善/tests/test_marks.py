"""印の買い方（印の付け方・印のルールの点数・勝負するレース・押さえ・期待値のカット・控えめな見積もり）。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_NO, RACE_DATE, RACE_ID

from 馬券の買い方の検証.analysis.ticket import TicketType

from 既存モデルの改善.analysis.betting import MarkCandidateBuilder, MarkPlan, MarkPlanChooser, RaceSelector, ShakyFavorite
from 既存モデルの改善.analysis.betting.candidate_columns import COMBO, COVER, RACE, TICKET, VALUE
from 既存モデルの改善.analysis.betting.payout_table import PAYOUT
from 既存モデルの改善.analysis.betting.race_columns import CONFIDENCE, GRADED, HONMEI_DANGER, HONMEI_TOP3
from 既存モデルの改善.analysis.combined.horse_columns import FORM_PROBABILITY, FORM_SHIFT, WIN_PROBABILITY
from 既存モデルの改善.analysis.market import CombinationTable
from 既存モデルの改善.analysis.marks import ALWAYS_RULES, COVER_RULES, DANGER, LONGSHOT_PLACE_VALUE, MARK, Mark, MarkAssigner
from 既存モデルの改善.analysis.race_probability import FinishOrderProbability
from 既存モデルの改善.analysis.scores import ConservativeRate

#: 印 → 馬番（△は3頭）。
_MARKED = {Mark.HONMEI: (1,), Mark.TAIKOU: (2,), Mark.TANANA: (3,), Mark.RENSHITA: (4, 5, 6), Mark.ANA: (7,),
           Mark.CHUI: (8,)}


def test_mark_rules_make_the_agreed_number_of_tickets():
    always = {rule.ticket: len(rule.combos(_MARKED)) for rule in ALWAYS_RULES}
    cover = {rule.ticket: len(rule.combos(_MARKED)) for rule in COVER_RULES}
    assert always == {TicketType.WIN: 1, TicketType.PLACE: 1, TicketType.QUINELLA: 5, TicketType.WIDE: 7,
                      TicketType.EXACTA: 10, TicketType.TRIO: 11, TicketType.TRIFECTA: 46}
    assert cover == {TicketType.QUINELLA: 1, TicketType.WIDE: 1, TicketType.EXACTA: 2, TicketType.TRIO: 5,
                     TicketType.TRIFECTA: 20}


def test_trifecta_swaps_first_second_and_second_third():
    cover = next(rule for rule in COVER_RULES if rule.ticket == TicketType.TRIFECTA)
    combos = set(cover.combos({Mark.TAIKOU: (2,), Mark.TANANA: (3,), Mark.RENSHITA: (4,)}))
    # ○→▲→△、▲→○→△（表裏）、○→△→▲（2・3着の入れ替え）、▲→△→○
    assert combos == {(2, 3, 4), (3, 2, 4), (2, 4, 3), (3, 4, 2)}


def _horses() -> pd.DataFrame:
    """1レース9頭。1番は危険な人気馬、9番は穴馬。"""
    return pd.DataFrame({
        RACE_ID: "R1", HORSE_NO: np.arange(1, 10),
        FORM_PROBABILITY: [0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10, 0.05],
        FORM_SHIFT: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.1, 0.3, 0.2],
        DANGER: [0.10, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        LONGSHOT_PLACE_VALUE: [np.nan] * 7 + [0.8, 1.3],
    })


def test_mark_assigner_drops_the_dangerous_favorite_and_moves_up():
    marks = MarkAssigner(exclude_line=0.05).assign(_horses()).set_index(HORSE_NO)[MARK]
    assert marks[2] == "◎" and marks[3] == "○" and marks[4] == "▲"
    assert list(marks[[5, 6, 7]]) == ["△"] * 3
    # 穴馬の複勝の期待値がいちばん高い 9番が ☆、残りで上げ下げが正の 8番が 注。消の 1番は印なし
    assert marks[9] == "☆" and marks[8] == "注" and pd.isna(marks[1])


def test_mark_assigner_without_line_keeps_everyone():
    marks = MarkAssigner(exclude_line=float("nan")).assign(_horses()).set_index(HORSE_NO)[MARK]
    assert marks[1] == "◎"


def _races() -> pd.DataFrame:
    return pd.DataFrame({
        RACE: ["a", "b", "c", "d"], RACE_DATE: pd.to_datetime(["2025-01-05"] * 3 + ["2025-01-06"]),
        CONFIDENCE: [1.3, 1.1, 0.9, 1.0], GRADED: [False, False, True, False],
        HONMEI_TOP3: [0.7, 0.45, 0.8, 0.9], HONMEI_DANGER: [np.nan, np.nan, 0.02, np.nan],
    })


def test_race_selector_takes_top_races_per_day_and_every_graded_race():
    chosen = _races()[RaceSelector(per_day=1).select(_races())][RACE].tolist()
    # 1月5日は上位1レース（a）と重賞（c）、1月6日は d
    assert chosen == ["a", "c", "d"]


def test_shaky_favorite_uses_the_line_and_the_danger():
    assert ShakyFavorite(0.5).of(_races()).tolist() == [False, True, True, False]
    assert ShakyFavorite(0.0).of(_races()).tolist() == [False, False, True, False]


def _candidates() -> pd.DataFrame:
    return pd.DataFrame({
        RACE: ["a", "a", "a", "b", "b"], TICKET: ["3連複"] * 5,
        COMBO: ["010203", "010204", "020304", "010203", "020304"],
        VALUE: [1.3, 0.85, 1.2, 1.1, 1.5], COVER: [False, False, True, False, True],
        PAYOUT: [3000.0, 0.0, 0.0, 0.0, 5000.0],
    })


def test_mark_plan_cuts_low_values_and_buys_cover_only_when_shaky():
    plan = MarkPlan(races_per_day=None, shaky_line=0.5, value_lines={"3連複": 1.0}, adopted=frozenset({"3連複"}))
    bought = plan.apply(_candidates(), _races())
    # a は◎が危うくないので押さえ（020304）は買わない。0.85 はカット。b は危ういので押さえも買う
    assert list(zip(bought[RACE], bought[COMBO])) == [("a", "010203"), ("b", "010203"), ("b", "020304")]
    assert plan.with_all_tickets().adopted == frozenset({"3連複"})
    assert MarkPlan(None, 0.5, {"3連複": 1.0}).apply(_candidates(), _races()).empty


def test_conservative_rate_is_lower_when_few_hits():
    days = pd.Series(np.arange(100) % 20)
    stake = pd.Series(100.0, index=days.index)
    steady = pd.Series(np.where(np.arange(100) % 2 == 0, 240.0, 0.0))
    lucky = pd.Series(np.where(np.arange(100) == 0, 12000.0, 0.0))
    rate = ConservativeRate()
    # どちらも回収率 120% だが、1回の大当たりだけのほうが控えめな見積もりは低い
    assert rate.of(days, stake, lucky) < rate.of(days, stake, steady) < 1.2


def test_plan_chooser_needs_enough_hits():
    races = pd.DataFrame({
        RACE: [f"r{index}" for index in range(60)], RACE_DATE: pd.to_datetime("2025-01-01") + pd.to_timedelta(np.arange(60) // 2, "D"),
        CONFIDENCE: 1.2, GRADED: False, HONMEI_TOP3: 0.7, HONMEI_DANGER: np.nan,
    })
    candidates = pd.DataFrame({
        RACE: races[RACE], TICKET: "単勝", COMBO: "01", VALUE: 1.2, COVER: False,
        PAYOUT: np.where(np.arange(60) % 2 == 0, 250.0, 0.0),
    })
    plan, choices = MarkPlanChooser(min_hits=30).choose(candidates, races)
    win = next(choice for choice in choices if choice.ticket == "単勝")
    assert win.hits == 30 and win.adopted and "単勝" in plan.adopted
    _, strict = MarkPlanChooser(min_hits=31).choose(candidates, races)
    assert np.isnan(next(choice for choice in strict if choice.ticket == "単勝").line)


def test_mark_candidate_builder_prices_the_marked_tickets():
    horses = pd.DataFrame({RACE_ID: "R1", HORSE_NO: [1, 2, 3], WIN_PROBABILITY: [0.5, 0.3, 0.2], MARK: ["◎", "○", "▲"]})
    win = pd.DataFrame({"race_id": "R1", "h1": [1, 2, 3], "odds": [1.8, 3.5, 6.0], "odds_high": [1.8, 3.5, 6.0]})
    quinella = pd.DataFrame({"race_id": "R1", "h1": [1, 1], "h2": [2, 3], "odds": [4.0, 9.0], "odds_high": [4.0, 9.0]})
    tables = {TicketType.WIN: CombinationTable(win, 1), TicketType.QUINELLA: CombinationTable(quinella, 2)}
    rules = [rule for rule in ALWAYS_RULES if rule.ticket in tables]
    built = MarkCandidateBuilder(tables, {}, FinishOrderProbability(), rules).build(horses)
    assert list(zip(built[TICKET], built[COMBO])) == [("単勝", "01"), ("馬連", "0102"), ("馬連", "0103")]
    assert built.loc[0, VALUE] == pytest.approx(0.5 * 1.8)
