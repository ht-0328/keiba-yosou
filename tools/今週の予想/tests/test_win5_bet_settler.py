"""Win5BetSettler（表1の WIN5 の行の精算）と、BetSettler が WIN5 の行を飛ばすことのテスト。合成DB の架空の WIN5 だけを使う。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from yosou.form_aptitude_win5_tickets.repository import Win5HistoryRepository
from yosou.form_aptitude_win5_tickets.repository.win5_columns import PAYOUT, RACE_DATE
from yosou.form_aptitude_win5_tickets.tests.win5_sample import FIELD_SIZE, FIRST_SUNDAY, FORECAST_DAY, Win5Sample
from yosou.review import BetSettler, ReviewStore, names

from 今週の予想.win5_bet_settler import Win5BetSettler
from 今週の予想.win5_combo import combo_text

#: 精算する過去の日曜（的中無でも返還でもない回）。
PAST_SUNDAY = FIRST_SUNDAY + timedelta(weeks=1)


@pytest.fixture(scope="module")
def sample() -> Win5Sample:
    builder = Win5Sample()
    builder.build()
    return builder


@pytest.fixture(scope="module")
def win5_db(sample: Win5Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return synth.build_db(tmp_path_factory.mktemp("win5_settle") / "win5.duckdb", sample.sample)


def _row(day: date, legs: list[tuple[int, ...]], stake: int) -> dict:
    return {names.RACE_ID: f"{day:%Y%m%d}05010107", names.TICKET_TYPE: names.WIN5_TICKET, names.COMBO: combo_text(legs),
            names.RACE_DATE: day, names.PARTICIPATION: names.POLICY_WIN5, names.RECORD_ONLY: False, names.STAKE_YEN: stake,
            names.BOUGHT_PROBABILITY: 0.01, names.BOUGHT_VALUE: 1.6, names.BOUGHT_ODDS: None, names.ODDS_AT: "t",
            names.PAYOUT_YEN: None, names.SETTLED: False}


def test_結果の入った日のWIN5を当たり組の払戻で精算し_結果の無い日は残す(sample: Win5Sample, win5_db: Path, tmp_path: Path) -> None:
    winners = sample.winners[PAST_SUNDAY]
    hit = [(number,) for number in winners]
    miss = [(number % FIELD_SIZE + 1,) for number in winners]
    store = ReviewStore(tmp_path / "review.duckdb")
    store.write(names.BETS_TABLE, pd.DataFrame([_row(PAST_SUNDAY, hit, 200), _row(PAST_SUNDAY - timedelta(weeks=1), miss, 100),
                                                _row(FORECAST_DAY, hit, 100)]))
    with db.open_db(win5_db) as con:
        assert Win5BetSettler(store).settle(con) == 2
        history = Win5HistoryRepository(con).read(PAST_SUNDAY + timedelta(days=1))
    per_100 = int(history.loc[history[RACE_DATE] == PAST_SUNDAY.isoformat(), PAYOUT].iloc[0])
    bets = store.read(names.BETS_TABLE).set_index(names.RACE_DATE)
    assert bets.loc[pd.Timestamp(PAST_SUNDAY), names.PAYOUT_YEN] == per_100 * 2
    assert bets.loc[pd.Timestamp(PAST_SUNDAY - timedelta(weeks=1)), names.PAYOUT_YEN] == 0
    assert not bets.loc[pd.Timestamp(FORECAST_DAY), names.SETTLED]


def test_レースの精算はWIN5の行を飛ばす(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "review.duckdb")
    store.write(names.BETS_TABLE, pd.DataFrame([_row(PAST_SUNDAY, [(1,), (2,), (3,), (4,), (5,)], 100)]))
    runs = pd.DataFrame({"race_id": [f"{PAST_SUNDAY:%Y%m%d}05010107"], "horse_no": [1], "finish": [1], "win_payout": [300],
                         "place_payout": [120], "frame_no": [1]})
    assert BetSettler(store).settle(runs) == 0
    assert not store.read(names.BETS_TABLE).iloc[0][names.SETTLED]
