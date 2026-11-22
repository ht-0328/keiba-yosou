"""FinalPredictor（出走の表とオッズの断面 → 印と買い目）と、DB を読む部品のテスト。モデルは偽物、DB はメモリの中の架空の表。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 高知ファイナルの買い目.final_columns import RAW_COLUMNS
from 高知ファイナルの買い目.final_features import FinalFeatures
from 高知ファイナルの買い目.final_predictor import FinalPredictor
from 高知ファイナルの買い目.repository import FinalRaceRepository, KochiRunRepository

from 高知ファイナルの買い目.testing.fake_models import FakeModels
from 高知ファイナルの買い目.testing.sample_runs import HORSES, SampleRuns

SAMPLE = SampleRuns()
RID = SAMPLE.rid(5, 3)


def _snapshot(scratched: int | None = None) -> pd.DataFrame:
    numbers = [no for no in range(1, HORSES + 1) if no != scratched]
    return pd.DataFrame({"horse_no": numbers, "odds_now": [2.0 * no for no in numbers], "place_low": [1.0 + 0.5 * no for no in numbers],
                         "announced": "02092040"})


def _predictor(models: FakeModels) -> FinalPredictor:
    runs = SAMPLE.build()
    return FinalPredictor(models, FinalFeatures().popularity_rates(runs))


def test_断面のオッズで人気を決め_割安な馬を本命にする() -> None:
    bets = _predictor(FakeModels({4: 0.4}, {2: 0.5, 3: 0.45})).bets(RID, SAMPLE.build(unrun=RID), _snapshot())
    assert (bets.head, bets.favorite, bets.partners[:2], bets.announced) == (4, 1, (2, 3), "02092040")
    assert round(bets.place_value, 2) == round(0.2 * 3.0, 2)


def test_断面にオッズの無い馬は_買い目に入らない() -> None:
    bets = _predictor(FakeModels({4: 0.4}, {2: 0.5, 3: 0.45})).bets(RID, SAMPLE.build(unrun=RID), _snapshot(scratched=2))
    assert 2 not in (bets.head, *bets.partners) and all(2 not in combo for combos in bets.tickets.values() for combo in combos)


def test_断面が無い_学んだ条件に合わないレースは_理由つきのなし() -> None:
    predictor = _predictor(FakeModels({}, {}))
    assert "断面がまだ無い" in predictor.bets(RID, SAMPLE.build(unrun=RID), pd.DataFrame()).reason
    short = SAMPLE.build(unrun=RID)
    short.loc[short["race_id"] == RID, "distance_m"] = 800
    assert "学んだ条件" in predictor.bets(RID, short, _snapshot()).reason


def test_高知の出走を読み_これから走るレースの出走馬を足す() -> None:
    con = duckdb.connect()
    runs = SAMPLE.build().assign(venue="高知")
    entries = runs[runs["race_id"] == RID]
    past = pd.concat([runs[runs["race_id"] != RID], runs.head(HORSES).assign(venue="園田", race_id="2025010550010101")])
    con.register("past_view", past)
    con.register("entry_view", entries)
    con.execute("CREATE TEMP TABLE facts AS SELECT * FROM past_view")
    con.execute("CREATE TEMP TABLE entries AS SELECT * FROM entry_view")
    repository = KochiRunRepository(con)
    assert list(repository.read().columns) == list(RAW_COLUMNS) and len(repository.read()) == len(runs) - HORSES
    assert len(repository.read("entries")) == len(runs) and RID in set(repository.read("entries")["race_id"])
    con.execute("INSERT INTO facts SELECT * FROM entry_view")
    assert len(repository.read("entries")) == len(runs)               # 事実表にもう入っているレースは足さない


def test_高知のその日の最後のレースで_名前にファイナルレースが入るときだけ_高知ファイナル() -> None:
    con = duckdb.connect()
    con.execute("CREATE TABLE ra (開催年 VARCHAR, 開催月日 VARCHAR, 競馬場コード VARCHAR, レース番号 VARCHAR, 競走名本題 VARCHAR, データ区分 VARCHAR, データ作成年月日 VARCHAR)")
    rows = [("2025", "0209", "54", "11", "一般", "2", "20250208"), ("2025", "0209", "54", "12", "ファイナルレース", "2", "20250208"),
            ("2025", "0216", "54", "11", "一般", "2", "20250215"), ("2025", "0216", "54", "12", "特別", "2", "20250215"),
            ("2025", "0209", "50", "12", "ファイナルレース", "2", "20250208")]
    con.executemany("INSERT INTO ra VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    repository = FinalRaceRepository(con)
    assert repository.is_final("2025020954010112")
    assert not repository.is_final("2025020954010111")        # 最後のレースではない
    assert not repository.is_final("2025021654010112")        # 名前が違う
    assert not repository.is_final("2025020950010112")        # 高知ではない
