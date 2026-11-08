"""WIN5 の日・過去の WIN5・取消と除外・出走馬・ファイルのリポジトリのテスト。"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from 共通 import db

from ..repository import (
    LegRunnerRepository,
    PayoutEstimatorRepository,
    Win5DayRepository,
    Win5ForecastRecordRepository,
    Win5HistoryRepository,
    Win5ScratchRepository,
)
from ..repository.leg_runner_repository import HORSE_NO as RUNNER_NO
from ..repository.win5_columns import (
    CARRY,
    COMBO,
    HORSE_NO,
    INVERSE_SUMS,
    LEG,
    NO_HIT,
    PAYOUT,
    RACE_DATE,
    RACE_IDS,
    REFUNDED,
    SATURDAY,
    WINNER_ODDS,
)
from .win5_sample import (
    FIRST_SUNDAY,
    FORECAST_CARRY,
    FORECAST_DAY,
    NO_HIT_SUNDAY,
    REFUND_SUNDAY,
    SATURDAY_EVERY,
    SCRATCHED_HORSE,
    SCRATCHED_LEG,
    SUNDAY_COUNT,
    Win5Sample,
)


def test_WIN5の日を発売の順の対象レースとキャリーオーバーで読む(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        day = Win5DayRepository(con).read(FORECAST_DAY)
    text = FORECAST_DAY.strftime("%Y%m%d")
    assert day.race_ids == tuple(f"{text}050101{no}" for no in ("07", "08", "09", "10", "11"))
    assert day.carry == FORECAST_CARRY
    assert not day.is_saturday


def test_WIN5の無い日は取り込みを案内して止まる(win5_db: Path) -> None:
    with db.open_db(win5_db) as con, pytest.raises(LookupError, match="jvstore realtime"):
        Win5DayRepository(con).read(date(2030, 1, 1))


def test_過去のWIN5は成績の版だけを開催日より前で読み_当たり組の単勝オッズを並べる(win5_db: Path, win5_sample: Win5Sample) -> None:
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(FORECAST_DAY)
    saturdays = len(range(0, SUNDAY_COUNT, SATURDAY_EVERY))
    assert history[RACE_DATE].nunique() == SUNDAY_COUNT + saturdays
    assert history[RACE_DATE].max() < FORECAST_DAY.isoformat()
    first = history.loc[history[RACE_DATE] == FIRST_SUNDAY.isoformat()].iloc[0]
    winners = win5_sample.winners[FIRST_SUNDAY]
    assert first[COMBO] == "".join(f"{n:02d}" for n in winners)
    assert not first[SATURDAY] and first[CARRY] == 0
    assert len(first[RACE_IDS]) == 5
    expected_odds = [win5_sample.odds[(FIRST_SUNDAY, leg)][number] for leg, number in enumerate(winners, start=1)]
    assert first[WINNER_ODDS] == pytest.approx(expected_odds)
    expected_sum = sum(1.0 / value for value in win5_sample.odds[(FIRST_SUNDAY, 1)].values())
    assert first[INVERSE_SUMS][0] == pytest.approx(expected_sum)
    saturday = FIRST_SUNDAY - timedelta(days=1)
    assert bool(history.loc[history[RACE_DATE] == saturday.isoformat(), SATURDAY].iloc[0])


def test_的中無の回は払戻0で_返還の回は印つきで読む(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(FORECAST_DAY)
    no_hit = history.loc[history[RACE_DATE] == (FIRST_SUNDAY + timedelta(weeks=NO_HIT_SUNDAY)).isoformat()].iloc[0]
    assert bool(no_hit[NO_HIT]) and no_hit[PAYOUT] == 0
    refunded = history.loc[history[RACE_DATE] == (FIRST_SUNDAY + timedelta(weeks=REFUND_SUNDAY)).isoformat()].iloc[0]
    assert bool(refunded[REFUNDED])
    assert all(not math.isnan(value) for value in refunded[WINNER_ODDS])


def test_ある日より前だけを読む(win5_db: Path) -> None:
    before = FIRST_SUNDAY + timedelta(days=1)
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(before)
    assert set(history[RACE_DATE]) == {(FIRST_SUNDAY - timedelta(days=1)).isoformat(), FIRST_SUNDAY.isoformat()}


def test_取消の馬番を何レース目とともに読む(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        scratches = Win5ScratchRepository(con).read(FORECAST_DAY)
    assert scratches.to_dict("records") == [{
        RACE_DATE: (FIRST_SUNDAY + timedelta(weeks=REFUND_SUNDAY)).isoformat(), LEG: SCRATCHED_LEG, HORSE_NO: SCRATCHED_HORSE,
    }]


def test_出走馬は取消を除いて馬番の順に読む(win5_db: Path) -> None:
    day = FIRST_SUNDAY + timedelta(weeks=REFUND_SUNDAY)
    with db.open_db(win5_db) as con:
        race_ids = Win5DayRepository(con).read(day).race_ids
        runners = LegRunnerRepository(con).read(race_ids[SCRATCHED_LEG - 1])
    assert runners[RUNNER_NO].tolist() == [number for number in range(1, 9) if number != SCRATCHED_HORSE]


def test_配当の見積もりの式のファイルは無ければfit_payoutを案内する(tmp_path: Path) -> None:
    repository = PayoutEstimatorRepository(tmp_path)
    with pytest.raises(FileNotFoundError, match="fit-payout"):
        repository.load()
    repository.save({"切片": 1.0}, {"この日より前": "2026-11-08"})
    assert repository.load() == {"切片": 1.0}
    assert b"\r\n" not in repository.path.read_bytes()


def test_予想の記録を開催日ごとに書いて読む(tmp_path: Path) -> None:
    repository = Win5ForecastRecordRepository(tmp_path)
    path = repository.save({"開催日": "2024-05-26", "判断": "見送り"}, date(2024, 5, 26))
    assert path == tmp_path / "記録" / "2024-05-26.json"
    assert repository.load(date(2024, 5, 26))["判断"] == "見送り"
    with pytest.raises(FileNotFoundError):
        repository.load(date(2024, 6, 2))
