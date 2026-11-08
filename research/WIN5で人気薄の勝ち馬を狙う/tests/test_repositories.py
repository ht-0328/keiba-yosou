"""元DB を読むリポジトリと、事例の研究の流れ全体を、合成DB で確かめる（実DB には触らない）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from 合成DB import synth
from 共通 import db

from WIN5で人気薄の勝ち馬を狙う.analysis.case_study import CaseStudy, CaseStudySettings
from WIN5で人気薄の勝ち馬を狙う.analysis.repository import RunnerFactsRepository, Win5LegRepository


def _win5_db(path: Path) -> Path:
    rows = synth.sample()
    first = synth.race("20240406", "01")
    second = synth.race("20240406", "02")
    cancelled = synth.race("20240407", "01")
    rows.win5 = [synth.win5_day("20240406"), synth.win5_day("20240407", stage="9")]
    rows.win5_races = [synth.win5_race("20240406", 1, first), synth.win5_race("20240406", 2, second),
                       synth.win5_race("20240407", 1, cancelled)]
    return synth.build_db(path, rows)


def test_WIN5の対象レースを読み_中止の回は読まない(tmp_path):
    with db.open_db(_win5_db(tmp_path / "w.duckdb")) as con:
        legs = Win5LegRepository(con).load(date(2024, 1, 1))
    assert legs["race_date"].tolist() == ["2024-04-06", "2024-04-06"]
    assert legs["leg"].tolist() == [1, 2]
    assert legs["race_id"].tolist() == ["2024040605010101", "2024040605010102"]


def test_出走の行は出走した馬だけで_数の列は小数(tmp_path):
    with db.open_db(synth.sample_db(tmp_path / "s.duckdb")) as con:
        runners = RunnerFactsRepository(con).load(date(2024, 1, 1))
    assert len(runners) == 6 * 5                     # 6レース × 出走5頭（取消は除く）
    assert runners["popularity"].dtype == "float64"
    assert set(runners["surface"]) == {"芝", "ダート"}


def test_流れ全体が人気薄のいない合成DBでも最後まで書ける(tmp_path):
    predictions = tmp_path / "win.pkl"
    pd.DataFrame({
        "レースID": ["2024040605010101"] * 5, "開催日": ["2024-04-06"] * 5, "馬ID": [f"2020{n:06d}" for n in range(1, 6)],
        "馬番": list(range(1, 6)), "確率": [0.4, 0.2, 0.2, 0.1, 0.1], "区切り": ["2024年前半"] * 5, "期間": ["テスト"] * 5,
        "区分": ["当日"] * 5,
    }).to_pickle(predictions)
    settings = CaseStudySettings(date_from=date(2024, 1, 1), history_from=date(2023, 1, 1), focus_date="2024-04-06",
                                 predictions=predictions, records=tmp_path / "記録なし")
    with db.open_db(_win5_db(tmp_path / "w.duckdb")) as con:
        path = CaseStudy(con, settings).run(tmp_path / "out")
    text = path.read_text(encoding="utf-8")
    assert "## 事例の数" in text and "## 詳しく見る日" in text
    assert (tmp_path / "out" / "WIN5の事例.csv").exists()
