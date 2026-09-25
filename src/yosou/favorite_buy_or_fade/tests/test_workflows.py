"""学習・1年ごとの評価・予測の流れと、コマンドの入口。"""

from __future__ import annotations

from pathlib import Path

import pytest

from yosou.shared.dataset import HORSE_NO
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..decision import BET_KINDS, DECISION
from ..repository import MODEL_FILE, SETTINGS_FILE
from ..similarity import SCORE_COLUMNS, UNIT
from ..workflow import YEAR, SimilarityTraining, YearlyEvaluation

#: 確定前の 1R で、利用者が渡す全頭の単勝オッズ（馬番 3 が1番人気）。
GIVEN_ODDS = ["3:2.2", "5:3.4", "1:4.5", "2:9.0", "4:12.0", "6:20.0", "7:30.0"]


def test_training_makes_three_models_per_unit(training_data, small_settings):
    models = SimilarityTraining(small_settings).train(training_data)
    # 架空のシーズンは 芝1600・芝2000・ダート1400・ダート1600。頭数が足りる距離は、どれも単位になる
    assert set(models.units) == {"芝1600m", "芝2000m", "ダート1400m", "ダート1600m"}
    rows = models.units["芝1600m"].group_rows()
    assert rows["勝利"] <= rows["馬券内"] and rows["馬券内"] + rows["馬券外"] > 0
    scores = models.scores(training_data.features)
    assert scores[list(SCORE_COLUMNS.values())].stack().between(0, 100).all()


def test_yearly_evaluation_trains_only_on_the_years_before(training_data, small_settings):
    rows = YearlyEvaluation(small_settings).run(training_data)
    assert set(rows[YEAR]) == {2024}
    assert len(rows) == len(training_data.between(None, None).ids.query("開催日.dt.year == 2024"))
    assert set(rows[DECISION]) <= set(BET_KINDS)
    # 2023年（10〜12月）の頭数は少ないので、芝ダートごとに1つの単位にまとまる
    assert rows[UNIT].nunique() == 2


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_evaluates_and_writes_the_tables(season_db: Path, small_settings_path: Path, tmp_path: Path):
    out, rows_out = tmp_path / "evaluation.md", tmp_path / "rows.csv"
    code = _run_command(["evaluate", "--config", str(small_settings_path), "--db", str(season_db),
                         "--out", str(out), "--rows-out", str(rows_out)])
    text = out.read_text(encoding="utf-8")
    assert code == 0 and "年ごとの結果" in text and "| 2024 |" in text and "判定ごとの成績" in text
    assert rows_out.exists()


def test_command_trains_and_predicts_a_card(season_db: Path, small_settings_path: Path, tmp_path: Path, capsys):
    models = tmp_path / "models"
    assert _run_command(["train", "--config", str(small_settings_path), "--db", str(season_db),
                         "--models", str(models), "--out", str(tmp_path / "train.md")]) == 0
    assert (models / MODEL_FILE).exists() and (models / SETTINGS_FILE).exists()
    code = _run_command(["predict", season.CARD_RACE_ID, "--odds", *GIVEN_ODDS, "--db", str(season_db),
                         "--models", str(models), "--format", "csv"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 1
    assert lines[0].startswith(f"{HORSE_NO},馬名,{UNIT},") and lines[0].endswith(DECISION)
    assert lines[1].startswith("3,")


def test_command_reports_missing_models(season_db: Path, tmp_path: Path, capsys):
    code = _run_command(["predict", season.CARD_RACE_ID, "--db", str(season_db), "--models", str(tmp_path)])
    assert code == 1 and "train" in capsys.readouterr().err
