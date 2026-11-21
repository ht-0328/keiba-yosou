"""事例の表（配当の帯・近走の文・事例の一覧）を架空の値で、段1・段2 の流れを地方の合成DB で確かめる。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 合成DB import local_synth, synth
from 地方の万馬券.analysis.outcome_pattern_table import PATTERN_COUNTS
from 地方の万馬券.analysis.payout_band import BIG, SOLID
from 高知ファイナルの高配当.analysis.case_list_table import CaseListTable
from 高知ファイナルの高配当.analysis.case_study import CaseStudy
from 高知ファイナルの高配当.analysis.final_race import RACE_NAME_KEY
from 高知ファイナルの高配当.analysis.final_runners import FinalRunners
from 高知ファイナルの高配当.analysis.kochi_run_features import KochiRunFeatures
from 高知ファイナルの高配当.analysis.payout_band_table import PayoutBandTable
from 高知ファイナルの高配当.analysis.recent_runs_text import RecentRunsText
from 高知ファイナルの高配当.analysis.theory_study import THEORY_CSV, TheoryStudy, TheoryStudySettings

from .sample_runs import FIELD_SIZE, kochi_runs

_KOCHI_CODE = "54"
_DAYS = ("20250105", "20250112", "20250119")
_HEADS = 9


def _tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    runs = KochiRunFeatures().build(kochi_runs())
    return runs, FinalRunners(min_heads=FIELD_SIZE).select(runs)


def test_配当の帯の表は帯ごとのレース数と全部の行():
    races = pd.DataFrame({"payout_band": [BIG, BIG, SOLID], "trifecta_payout": [150_000, 250_000, 3_000]})
    table = PayoutBandTable().build(races, title="t")
    rows = {row[0]: row for row in table.rows}
    assert rows[BIG][1:] == [2, "66.7%", 200_000]
    assert rows["全部"][1] == 3


def test_近走の文はそのレースより前の走だけを古い順に並べる():
    runs, runners = _tables()
    days = sorted(runners["race_date"].unique())
    first_day = runners[runners["race_date"] == days[0]]
    third_day = runners[runners["race_date"] == days[2]]
    assert RecentRunsText().texts(runs, first_day).str.contains("出走なし").all()
    texts = RecentRunsText().texts(runs, third_day)
    assert (texts.str.count("F C2") == 2).all()                 # 前の2回のファイナルだけ。今回の走は入らない
    assert RecentRunsText(count=1).texts(runs, third_day).str.count("F C2").eq(1).all()


def test_事例の一覧は配当の高い順にレースごとの表を作る():
    runs, runners = _tables()
    races = runners.groupby("race_id")[["race_date", "class_name", "distance_m", "condition", "field_size"]].first()
    races["trifecta_payout"] = range(10_000, 10_000 + len(races))
    races[PATTERN_COUNTS] = "人1中1大1"
    tables = CaseListTable(limit=2).build(runs, runners, races)
    assert len(tables) == 2
    assert f"{races['trifecta_payout'].max():,}円" in tables[0].title
    assert len(tables[0].rows) == FIELD_SIZE
    assert [row[0] for row in tables[0].rows] == [str(place) for place in range(1, FIELD_SIZE + 1)]   # 着順の順


def _kochi_db(path: Path) -> Path:
    """高知の3日（1日に条件戦1つとファイナルレース1つ、9頭）の合成DB。"""
    sample = synth.Sample()
    for day in _DAYS:
        for no, name in (("01", ""), ("02", f"{RACE_NAME_KEY}　Ｃ３")):
            race_row = local_synth.local_race(day, no, venue=_KOCHI_CODE, distance="1400", name=name,
                                              field_size=f"{_HEADS:02d}", entries=f"{_HEADS:02d}", condition_name="Ｃ３　一")
            sample.ra.append(race_row)
            _add_runners(sample, race_row, first_horse=1 if no == "01" else 101)
    return synth.build_db(path, sample)


def _add_runners(sample: synth.Sample, race_row: dict[str, str], *, first_horse: int) -> None:
    """馬番 = 人気。着順は人気の逆（9番人気が1着）。"""
    for num in range(1, _HEADS + 1):
        finish = _HEADS + 1 - num
        hid = f"2020{first_horse + num:06d}"
        sample.se.append(local_synth.local_runner(race_row, num, num, finish, hid=hid, name=f"ウマ{first_horse + num}",
                                                  odds=f"{20 * num:04d}"))
        sample.nu.append(local_synth.local_horse(hid, f"ウマ{first_horse + num}"))
    sample.win.append(synth.payout(race_row, _HEADS, 1800))
    sample.trifecta.append(synth.combo_payout(race_row, "090807", 250_000))


def test_段1と段2の流れが合成DBで最後まで動く(tmp_path: Path):
    con = duckdb.connect(str(_kochi_db(tmp_path / "kochi.duckdb")), read_only=True)
    try:
        cases = CaseStudy(con).run(tmp_path / "out")
        theories = TheoryStudy(con, TheoryStudySettings(min_runs=1, min_period_runs=1)).run(tmp_path / "out")
    finally:
        con.close()
    case_text = cases.read_text(encoding="utf-8")
    assert "250,000円" in case_text and "型 人0中1大2" in case_text      # 9・8・7番人気で決まった 9頭のレース
    assert "ファイナル初出走" in theories.read_text(encoding="utf-8")
    assert (tmp_path / "out" / THEORY_CSV).exists()
