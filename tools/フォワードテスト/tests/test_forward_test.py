"""フォワードテストの記録・精算・開催日の追い方のテスト。合成DB と、待つと進む偽の時計だけを使う。"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

import duckdb
import pytest

from 共通.render import Table
from 合成DB import synth
from フォワードテスト.clock import Clock
from フォワードテスト.forward_follower import ForwardFollower
from フォワードテスト.ledger import REFUNDED, SETTLED, Ledger
from フォワードテスト.settlement import Settlement

DAY = "2024-04-06"


def _race_id(sample: synth.Sample) -> str:
    ra = sample.ra[0]
    return "".join(ra[name] for name in synth.KEY_COLUMNS)


def _buy(race_id: str, horse_no: int) -> dict[str, object]:
    return {"記録時刻": "2024-04-06 09:50", "開催日": DAY, "race_id": race_id, "発走": "10:00", "場": "東京", "R": 1,
            "馬番": horse_no, "馬名": f"馬{horse_no}", "期待値": 1.3, "線": 1.2, "モデル": "馬体重あり", "賭け金": 100,
            "払戻": "", "精算": "", "精算時刻": ""}


def test_記録は足すたびに残り_予想したレースも数えられる(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.append([_buy("R1", 3)], {"race_id": "R1", "買い目の数": 1})
    ledger.append([], {"race_id": "R2", "買い目の数": 0, "予想できない理由": "馬体重が未発表"})
    assert ledger.recorded_races() == {"R1", "R2"}
    assert list(ledger.buys()["馬番"]) == ["3"]


def test_結果が出た買い目を精算し_取消は返還する(tmp_path) -> None:
    # 合成の1レース: 馬番1 は4着、2 は2着（複勝 180円）、5 は競走中止、6 は出走取消。
    sample = synth.simple_race("20240406", "01")
    sample.headers = [synth.payout_header(sample.ra[0])]
    path = synth.build_db(tmp_path / "db.duckdb", sample)
    race_id = _race_id(sample)
    ledger = Ledger(tmp_path / "ledger")
    ledger.append([_buy(race_id, number) for number in (1, 2, 5, 6)], {"race_id": race_id, "買い目の数": 4})
    con = duckdb.connect(str(path), read_only=True)
    try:
        settled = Settlement(ledger).settle(con, datetime(2024, 4, 6, 17, 0))
    finally:
        con.close()
    buys = ledger.buys().set_index("馬番")
    assert settled == 4
    assert buys.loc["2", "払戻"] == "180" and buys.loc["2", "精算"] == SETTLED
    assert buys.loc["1", "払戻"] == "0" and buys.loc["5", "払戻"] == "0", "4着と競走中止は外れ"
    assert buys.loc["6", "払戻"] == "100" and buys.loc["6", "精算"] == REFUNDED, "出走取消は返還"


def test_結果がまだのレースは精算しない(tmp_path) -> None:
    sample = synth.simple_race("20240406", "01")  # 払戻の親（hr）が無い = 結果がまだ
    path = synth.build_db(tmp_path / "db.duckdb", sample)
    ledger = Ledger(tmp_path / "ledger")
    ledger.append([_buy(_race_id(sample), 2)], {"race_id": _race_id(sample), "買い目の数": 1})
    con = duckdb.connect(str(path), read_only=True)
    try:
        assert Settlement(ledger).settle(con, datetime(2024, 4, 6, 17, 0)) == 0
    finally:
        con.close()
    assert ledger.buys()["精算"].tolist() == [""]


class FakePredictor:
    """2レース（10:00・10:30 発走）を返し、どのレースでも馬番3 の期待値を 1.5 にする予想。"""

    def __init__(self, fake_time: "FakeTime") -> None:
        self.predicted: list[tuple[str, datetime]] = []
        self._time = fake_time

    def load_models(self) -> list:
        return []

    def races(self, con, day: str, after: str) -> list[dict]:
        return [{"rid": "R1", "発走": "10:00", "場": "東京", "R": 1, "レース名": ""},
                {"rid": "R2", "発走": "10:30", "場": "東京", "R": 2, "レース名": ""}]

    def predict(self, con, race_id: str, loaded: list) -> tuple[str, Table]:
        self.predicted.append((race_id, self._time.current))
        return "馬体重あり", Table(["馬番", "馬名", "使用した人気", "期待値"], [[3, "馬3", 5, 1.5], [4, "馬4", 6, 0.9]])


class FakeTime:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def clock(self) -> Clock:
        return Clock(now=lambda: self.current, sleep=self._sleep)

    def _sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=max(seconds, 1.0))


@contextmanager
def _empty_db():
    con = duckdb.connect()
    try:
        yield con
    finally:
        con.close()


def _follow(tmp_path, start: datetime) -> tuple[FakePredictor, Ledger, FakeTime]:
    fake = FakeTime(start)
    predictor, ledger = FakePredictor(fake), Ledger(tmp_path)
    ForwardFollower(predictor, ledger, _empty_db, line=1.2, clock=fake.clock(), log=lambda _: None).run("2024-04-06")
    return predictor, ledger, fake


def test_各レースを発走の10分前に1回だけ予想して記録する(tmp_path) -> None:
    predictor, ledger, _ = _follow(tmp_path, datetime(2024, 4, 6, 8, 0))
    assert [race_id for race_id, _ in predictor.predicted] == ["R1", "R2"]
    for (race_id, at), post in zip(predictor.predicted, (datetime(2024, 4, 6, 10, 0), datetime(2024, 4, 6, 10, 30))):
        assert post - timedelta(minutes=10) <= at < post, race_id
    assert ledger.buys()["馬番"].tolist() == ["3", "3"], "期待値が線以上の馬だけを買い目にする"


def test_発走を過ぎたレースと記録済みのレースは予想しない(tmp_path) -> None:
    predictor, _, _ = _follow(tmp_path, datetime(2024, 4, 6, 10, 5))
    assert [race_id for race_id, _ in predictor.predicted] == ["R2"]
    again, _, _ = _follow(tmp_path, datetime(2024, 4, 6, 10, 25))
    assert again.predicted == [], "やり直しても二重に記録しない"


def test_結果が出なければ最後の発走から3時間で精算をあきらめて終わる(tmp_path) -> None:
    _, ledger, fake = _follow(tmp_path, datetime(2024, 4, 6, 8, 0))
    assert fake.current >= datetime(2024, 4, 6, 13, 30)
    assert (tmp_path / "成績.md").is_file() and set(ledger.buys()["精算"]) == {""}


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """偽の時計を渡し忘れたテストが、本当に待たないようにする。"""
    monkeypatch.setattr("time.sleep", lambda seconds: (_ for _ in ()).throw(AssertionError("本当に待とうとした")))
