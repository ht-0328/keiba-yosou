"""過去の WIN5 での精算と、比べる相手の買い目・成績の表のテスト。"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd

from 共通 import db

from ..formation import Formation
from ..payout import PAYOUT_CEILING
from ..repository import Win5HistoryRepository, Win5ScratchRepository
from ..settlement import (
    HIT,
    PAYOUT,
    PERIOD,
    RACE_DATE,
    STAKE,
    STRATEGY,
    PopularityFormation,
    RuleFormations,
    Win5BacktestTables,
    Win5Outcome,
    Win5Outcomes,
    Win5Settlement,
)
from .win5_sample import FIRST_SUNDAY, FORECAST_DAY, NO_HIT_SUNDAY, REFUND_SUNDAY, SCRATCHED_HORSE, SCRATCHED_LEG, Win5Sample

NOTHING = (frozenset(),) * 5


def _outcome(winners, *, no_hit: bool = False, scratched=NOTHING, votes: int = 1_000_000, carry: int = 0) -> Win5Outcome:
    return Win5Outcome("2024-05-26", winners, no_hit, scratched, votes, carry)


def test_当たり組を含めば払戻を受け取り_含まなければ0() -> None:
    formation = Formation(((3, 7), (5,), (1, 2), (4,), (6, 8)))
    hit = Win5Settlement().settle(formation, _outcome((((7, 5, 2, 4, 6), 123_400),)))
    assert (hit.points, hit.stake, hit.payout, hit.hit, hit.refunded_points) == (8, 800, 123_400, True, 0)
    miss = Win5Settlement().settle(formation, _outcome((((7, 5, 9, 4, 6), 123_400),)))
    assert (miss.payout, miss.hit) == (0, False)


def test_同着で当たり組が2つなら両方の払戻() -> None:
    formation = Formation(((3, 7), (5,), (1, 2), (4,), (6, 8)))
    settled = Win5Settlement().settle(formation, _outcome((((3, 5, 1, 4, 6), 1000), ((3, 5, 2, 4, 6), 2000))))
    assert settled.payout == 3000


def test_取消の馬を含む組は代金が戻る() -> None:
    formation = Formation(((3, 7), (5,), (1, 2), (4,), (6, 8)))
    scratched = (frozenset({7}), frozenset(), frozenset(), frozenset(), frozenset())
    settled = Win5Settlement().settle(formation, _outcome((((3, 5, 1, 4, 6), 5000),), scratched=scratched))
    assert settled.refunded_points == 4
    assert settled.payout == 5000 + 4 * 100


def test_的中無の回に当たり組を買っていたら払戻に回るお金を1票で受け取る() -> None:
    formation = Formation(((3,), (5,), (1,), (4,), (6,)))
    settled = Win5Settlement().settle(formation, _outcome((((3, 5, 1, 4, 6), 0),), no_hit=True, votes=1_000_000, carry=5_000_000))
    assert settled.payout == 75_000_000
    huge = Win5Settlement().settle(formation, _outcome((((3, 5, 1, 4, 6), 0),), no_hit=True, votes=10_000_000_000))
    assert huge.payout == PAYOUT_CEILING


def test_ルール集のWIN5のルールは48点を5セットの240点() -> None:
    popularity = [list(range(1, 11))] * 5
    sets = RuleFormations().of(popularity)
    assert [each.points for each in sets] == [48] * 5
    assert sets[0].legs[0] == (4, 5, 6) and sets[0].legs[1] == (1, 2)
    assert len({combo for each in sets for combo in each.combos()}) == 240


def test_人気だけの買い目は頭数をそろえて予算に収める() -> None:
    popularity = [list(range(1, 11))] * 5
    assert PopularityFormation().of(popularity, 100).sizes == (4, 3, 2, 2, 2)
    assert PopularityFormation().of(popularity, 32).sizes == (2, 2, 2, 2, 2)
    short = [[1, 2], *[list(range(1, 11))] * 4]
    assert PopularityFormation().of(short, 500).sizes[0] == 2


def test_過去のWIN5の表から回ごとの結果を作り_合成DBの当たり組と取消で精算する(win5_db: Path, win5_sample: Win5Sample) -> None:
    with db.open_db(win5_db) as con:
        outcomes = Win5Outcomes().of(Win5HistoryRepository(con).read(FORECAST_DAY), Win5ScratchRepository(con).read(FORECAST_DAY))
    refund_day = FIRST_SUNDAY + timedelta(weeks=REFUND_SUNDAY)
    outcome = outcomes[refund_day.isoformat()]
    assert outcome.winners[0][0] == win5_sample.winners[refund_day]
    assert outcome.scratched[SCRATCHED_LEG - 1] == frozenset({SCRATCHED_HORSE})
    assert outcomes[(FIRST_SUNDAY + timedelta(weeks=NO_HIT_SUNDAY)).isoformat()].no_hit
    winners = win5_sample.winners[refund_day]
    legs = [(number,) for number in winners]
    legs[SCRATCHED_LEG - 1] = (winners[SCRATCHED_LEG - 1], SCRATCHED_HORSE)
    settled = Win5Settlement().settle(Formation(tuple(legs)), outcome)
    assert settled.hit and settled.refunded_points == 1
    assert settled.payout == outcome.winners[0][1] + 100


def test_成績の表は買い方ごと期間ごとと年ごと() -> None:
    settled = pd.DataFrame([
        {STRATEGY: "A", PERIOD: "探索", RACE_DATE: "2019-05-26", STAKE: 10_000, PAYOUT: 0, HIT: False},
        {STRATEGY: "A", PERIOD: "探索", RACE_DATE: "2020-05-31", STAKE: 10_000, PAYOUT: 30_000, HIT: True},
        {STRATEGY: "B", PERIOD: "確認", RACE_DATE: "2025-06-01", STAKE: 24_000, PAYOUT: 0, HIT: False},
    ])
    by_period, by_year = Win5BacktestTables().tables(settled)
    assert by_period.rows[0][:7] == ["A", "探索", 2, 20_000, 30_000, "150.0%", "50.0%"]
    assert [row[1] for row in by_year.rows] == ["2019年", "2020年", "2025年"]
