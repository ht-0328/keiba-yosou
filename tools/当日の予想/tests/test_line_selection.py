import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from line_selection import MIN_BETS, LineSelection  # noqa: E402


def _result(bets: int, lower: float | None) -> dict:
    return {"点数": bets, "複勝回収率の下限": lower}


def test_picks_the_lowest_line_that_reaches_in_the_choosing_period_and_confirms_it():
    choose = {1.2: _result(500, 0.95), 1.3: _result(300, 1.01), 1.5: _result(150, 1.10)}
    confirm = {1.2: _result(400, 1.20), 1.3: _result(250, 1.02), 1.5: _result(120, 0.90)}
    decision = LineSelection().decide(choose, confirm)
    assert decision.line == 1.3, "確かめる期間の結果（1.2 が良い）では選ばない"


def test_no_line_when_the_chosen_line_fails_in_the_confirming_period():
    choose = {1.2: _result(500, 1.05), 1.3: _result(300, 1.20)}
    confirm = {1.2: _result(400, 0.97), 1.3: _result(250, 1.10)}
    decision = LineSelection().decide(choose, confirm)
    assert decision.line is None and "確かめる期間" in decision.reason


def test_too_few_bets_or_no_lower_bound_does_not_reach():
    choose = {1.2: _result(MIN_BETS - 1, 1.50), 1.3: _result(MIN_BETS, None)}
    decision = LineSelection().decide(choose, dict(choose))
    assert decision.line is None and "選ぶ期間" in decision.reason
