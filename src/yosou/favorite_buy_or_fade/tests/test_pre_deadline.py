"""締め切り前のオッズで1番人気を選んだときの評価（設計書 16 の 7）。

架空の1シーズンの 2024年のレースのうち、はじめの数レースに締め切り前の単勝オッズの断面を足した合成DB を使う。
偶数番目のレースは締め切り前に2番人気の馬が1番人気になり、奇数番目のレースは確定と同じ馬が1番人気になる。
締め切りの 10分前より後の断面（中間）と、締め切りの時点の断面（最終）は、確定の1番人気がいちばん低いオッズにしておき、
読まれないことを確かめる。
"""

from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from yosou.shared.dataset import HORSE_NO, RACE_ID

from ..command import CommandLine
from ..dataset import CONFIRMED, PICK, PRE_DEADLINE, FavoritePicks, PreDeadlineFavorites
from ..repository import PreDeadlineFavoriteRepository
from ..workflow import TrainingDataReader, YearlyEvaluation

#: 断面を足すレースの数（2024年のはじめの、障害でないレースから）。
_RACES = 6
#: トラックコードがこれ以上なら障害レース（学習データに入らない）。
_JUMP_TRACKS = 50
#: 単勝オッズの子の表。
_WIN_ODDS = "o1__単勝オッズ"
#: 足す断面（データ区分・発表の時分・どちらの馬を1番人気にするか）。発走は 15:00 なので、10分前の締めは 14:50。
_SNAPSHOTS = (("1", "1440", "picked"), ("1", "1455", "confirmed"), ("3", "1459", "confirmed"))


def _race_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[name] for name in synth.KEY_COLUMNS)


def _favorites(sample: synth.Sample, race_row: dict[str, str], index: int) -> dict[str, str]:
    """そのレースの、確定の1番人気と、締め切り前に1番人気にする馬（偶数番目のレースは2番人気の馬）の馬番。"""
    by_popularity = {r["単勝人気順"]: r["馬番"] for r in sample.se if _race_key(r) == _race_key(race_row)}
    return {"confirmed": by_popularity["01"], "picked": by_popularity["02" if index % 2 == 0 else "01"]}


def _snapshot(sample: synth.Sample, race_row: dict[str, str], stage: str, announced: str, favorite: str) -> list:
    """1つの断面（親1行と、出走馬ごとの単勝オッズ）。``favorite`` の馬だけオッズを低くする。"""
    runners = [r["馬番"] for r in sample.se if _race_key(r) == _race_key(race_row)]
    odds = [(_WIN_ODDS, synth.odds_row(race_row, _WIN_ODDS, number, 20 if number == favorite else 80, announced=announced))
            for number in runners]
    return [("o1", synth.odds_header(race_row, "o1", stage=stage, announced=announced)), *odds]


@pytest.fixture(scope="module")
def snapshot_races(season_sample: synth.Sample) -> list[tuple[dict[str, str], dict[str, str]]]:
    """断面を足すレースの行と、そのレースの1番人気の馬番。"""
    races = [r for r in season_sample.ra if r["開催年"] == "2024" and int(r["トラックコード"]) < _JUMP_TRACKS][:_RACES]
    return [(race_row, _favorites(season_sample, race_row, index)) for index, race_row in enumerate(races)]


@pytest.fixture(scope="module")
def snapshot_db(season_sample: synth.Sample, snapshot_races, tmp_path_factory: pytest.TempPathFactory) -> Path:
    sample = copy.deepcopy(season_sample)
    for race_row, favorites in snapshot_races:
        sample.odds.extend(
            row for stage, time, who in _SNAPSHOTS
            for row in _snapshot(season_sample, race_row, stage, race_row["開催月日"] + time, favorites[who])
        )
    return synth.build_db(tmp_path_factory.mktemp("pre-deadline") / "season.duckdb", sample)


def test_repository_reads_the_latest_snapshot_before_the_cutoff(snapshot_db: Path, snapshot_races):
    with db.open_db(snapshot_db) as con:
        ten_minutes = PreDeadlineFavoriteRepository(con, 10).read()
        three_minutes = PreDeadlineFavoriteRepository(con, 3).read()
    expected = [int(favorites["picked"]) for _, favorites in snapshot_races]
    assert len(ten_minutes) == _RACES and ten_minutes["horse_no"].tolist() == expected
    # 3分前までなら 14:55 の断面（確定と同じ馬が1番人気）を使う。14:59 の最終の断面は使わない
    assert three_minutes["horse_no"].tolist() == [int(favorites["confirmed"]) for _, favorites in snapshot_races]


def test_yearly_evaluation_judges_both_picks_on_the_same_races(snapshot_db: Path, small_settings, snapshot_races):
    with db.open_db(snapshot_db) as con:
        pre_deadline = PreDeadlineFavorites(PreDeadlineFavoriteRepository(con, 10).read())
        data = TrainingDataReader(small_settings, pre_deadline).read(con)
    picks = FavoritePicks(pre_deadline)
    # 学習に使うのは確定の1番人気だけ（締め切り前に1番人気だった2番人気の馬は入れない）
    assert picks.training_rows(data).sum() == len(data) - _RACES // 2
    rows = YearlyEvaluation(small_settings, picks).run(data)
    assert rows[PICK].value_counts().to_dict() == {CONFIRMED: _RACES, PRE_DEADLINE: _RACES}
    pre_rows = rows[rows[PICK] == PRE_DEADLINE].sort_values(RACE_ID)
    assert pre_rows[HORSE_NO].astype(int).tolist() == [int(favorites["picked"]) for _, favorites in snapshot_races]


def test_command_compares_the_picks(snapshot_db: Path, small_settings_path: Path, tmp_path: Path):
    out, rows_out = tmp_path / "pre-deadline.md", tmp_path / "rows.csv"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(["evaluate", "--config", str(small_settings_path), "--db", str(snapshot_db),
                           "--favorite-odds", "締め切り前", "--out", str(out), "--rows-out", str(rows_out)])
    text = out.read_text(encoding="utf-8")
    assert stopped.value.code == 0 and "1番人気が入れ替わったレース" in text and "| 6 | 3 |" in text
    assert "選び方ごとの結果（1番人気が入れ替わったレースだけ）" in text and "年ごとの結果" in text
    assert set(pd.read_csv(rows_out, encoding="utf-8-sig")[PICK]) == {CONFIRMED, PRE_DEADLINE}
