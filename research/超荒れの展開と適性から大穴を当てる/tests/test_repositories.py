"""元DB とほかの置き場所を読むリポジトリと、事例の研究の流れ全体を、合成DB と一時ファイルで確かめる（実DB には触らない）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 合成DB import synth
from 共通 import db

from 超荒れの展開と適性から大穴を当てる.analysis.case_study import CASES_CSV, COURSE_CSV, CaseStudy, CaseStudySettings
from 超荒れの展開と適性から大穴を当てる.analysis.repository import (DisadvantageNoteRepository, PaceForecastStore,
                                                     PreClosePopularityRepository, RaceReviewRepository,
                                                     RunnerFactsRepository)


def test_出走の行は平地で出走した馬だけで_数の列は小数(tmp_path: Path):
    with db.open_db(synth.sample_db(tmp_path / "s.duckdb")) as con:
        runners = RunnerFactsRepository(con).load(date(2024, 1, 1))
    assert len(runners) == 6 * 5                     # 6レース × 出走5頭（取消は除く）
    assert runners["carried"].dtype == "float64"
    assert "first_corner_rank" in runners.columns


def test_締め切り前の人気はいちばん新しい断面を読む(tmp_path: Path):
    rows = synth.sample()
    ra = rows.ra[0]
    for at, popularity in (("04061000", 3), ("04061450", 11)):
        rows.odds.append(("o1", synth.odds_header(ra, "o1", stage="1", announced=at)))
        rows.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "04", 150, pop=popularity, announced=at)))
    with db.open_db(synth.build_db(tmp_path / "o.duckdb", rows)) as con:
        early = PreClosePopularityRepository(con).load(date(2024, 1, 1))
        later = PreClosePopularityRepository(con).load(date(2025, 1, 1))
    assert early["pre_close_popularity"].tolist() == [11.0]
    assert early["pre_close_odds"].tolist() == [15.0]
    assert early["horse_no"].tolist() == [4.0]
    assert later.empty                               # 読み始める日より前のレースは読まない


def test_回顧の表と展開の予想を読み_無ければ空(tmp_path: Path):
    path = tmp_path / "review.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute('CREATE TABLE "レースの回顧" (race_id VARCHAR, race_date DATE, "結果のペース" VARCHAR, '
                    '"当日の内の傾き" DOUBLE, "当日の前の傾き" DOUBLE)')
        con.execute("INSERT INTO \"レースの回顧\" VALUES ('r1', '2024-01-01', 'ハイ', 0.1, -0.2)")
        con.execute('CREATE TABLE "馬の回顧ノート" (race_id VARCHAR, horse_id VARCHAR, "不利の種類" VARCHAR, "程度" VARCHAR)')
        con.execute("INSERT INTO \"馬の回顧ノート\" VALUES ('r1', 'h1', '出遅れ', '大')")
    reviews = RaceReviewRepository(path).load()
    assert reviews.to_dict("records") == [{"race_id": "r1", "pace": "ハイ", "tilt_inner": 0.1, "tilt_front": -0.2}]
    assert DisadvantageNoteRepository(path).load()["disadvantage"].tolist() == ["出遅れ"]
    assert RaceReviewRepository(tmp_path / "none.duckdb").load().empty
    folder = tmp_path / "forecasts"
    folder.mkdir()
    pd.to_pickle({"races": pd.DataFrame({"レースID": ["r1"], "p_slow": [0.2], "p_even": [0.3], "p_high": [0.5]}),
                  "horses": pd.DataFrame({"レースID": ["r1"], "馬ID": ["h1"], "p_leader": [0.1], "p_front": [0.4],
                                          "p_middle": [0.4], "p_back": [0.2]})}, folder / "2024.pkl")
    store = PaceForecastStore(folder)
    assert store.races()["p_high"].tolist() == [0.5]
    assert store.horses()["horse_id"].tolist() == ["h1"]
    assert PaceForecastStore(tmp_path / "none").races().empty


def test_流れ全体は合成DBで表と事例の一覧を書く(tmp_path: Path):
    settings = CaseStudySettings(date_from=date(2024, 1, 1), history_from=date(2024, 1, 1), odds_from=date(2024, 1, 1),
                                 review_db=tmp_path / "none.duckdb", pace_forecasts=tmp_path / "none",
                                 case_counts={"大穴2頭以上": (2, 1)})
    study = CaseStudy(settings)
    with db.open_db(synth.sample_db(tmp_path / "s.duckdb")) as con:
        runners = study.load(con)
    path = study.write(runners, tmp_path / "out")
    assert path.exists()
    assert "## 1. 事例の数" in path.read_text(encoding="utf-8")
    assert (tmp_path / "out" / CASES_CSV).exists()
    assert (tmp_path / "out" / COURSE_CSV).exists()
