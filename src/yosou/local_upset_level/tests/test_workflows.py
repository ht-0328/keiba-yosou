"""学習の流れ（設計書 05 の図1）と発走前の1レースの予測（図2）、コマンドの入口。地方の合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 共通 import db, keys

from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import local_season as season
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import BET, PREDICTION_COLUMNS, TOP_LEVEL, UPSET_OR_MORE

from ..command import CommandLine
from ..workflow import TIMINGS, LocalUpsetForecast
from .conftest import TRAINED_BETS
from .test_dataset_builder import CARD_ODDS

#: 出馬表のレースに手で渡す単勝オッズ（``--odds`` の書き方）。
CARD_ODDS_TEXTS = [f"{horse_no}:{odds}" for horse_no, odds in CARD_ODDS.items()]


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return int(stopped.value.code or 0)


def _common(local_season_db: Path, models: Path, cache_dir: Path) -> list[str]:
    return ["--db", str(local_season_db), "--models", str(models), "--cache", str(cache_dir)]


def test_学習は券種ごと_3つの時点ごとに2つのモデルを保存する(trained: tuple[Path, str]):
    models, _ = trained
    expected = {SETTINGS_FILE, *(model_type.file_name for model_type in CLASS_MEMBER_TYPES)}
    for bet in TRAINED_BETS:
        for timing in TIMINGS:
            assert {path.name for path in (models / bet.key / timing.value).iterdir()} == expected
    assert not (models / BetType.QUINELLA.key).exists()


def test_学習の報告は_出馬表の名前と_線引きの表を出す(trained: tuple[Path, str]):
    _, report = trained
    assert "単勝: 検証データでの当たり具合" in report and "| 出馬表 |" in report and "| 木曜 |" not in report
    assert "3連単: 「荒れるレースだけ買う」使い方の線引き（検証データ）" in report and "荒れ具合（3連単）" in report


def test_発走前の1レースの荒れ具合は_券種ごとに4つの確率の合計が1(local_season_db: Path, trained: tuple[Path, str], cache_dir: Path):
    models, _ = trained
    forecast = LocalUpsetForecast(models, cache_dir)
    with db.open_db(local_season_db) as con:
        table = forecast.run(con, season.CARD_RACE_ID, PredictionTiming.RACE_DAY, OddsInput.of(CARD_ODDS_TEXTS), TRAINED_BETS)
        finished = con.execute(f"SELECT {keys.rid_expr()} FROM ra WHERE {keys.final_only()} ORDER BY 開催年, 開催月日, レース番号 LIMIT 1").fetchone()[0]
        upsets = forecast.upset_or_more(con, finished, bets=TRAINED_BETS)   # 終わったレースは確定オッズで出せる
    levels = list(UpsetLevel.labels())
    assert table[BET].tolist() == [bet.label for bet in TRAINED_BETS]
    assert list(table.columns)[-len(PREDICTION_COLUMNS):] == list(PREDICTION_COLUMNS)
    np.testing.assert_allclose(table[levels].sum(axis=1), 1.0)
    np.testing.assert_allclose(table[UPSET_OR_MORE], 1.0 - table["固い"])
    assert (table[TOP_LEVEL] == table[levels].idxmax(axis=1)).all()
    assert set(upsets) == set(TRAINED_BETS) and all(0.0 <= value <= 1.0 for value in upsets.values())


def test_predictは当日に全頭のオッズで_券種ごとの行を出す(local_season_db: Path, trained: tuple[Path, str], cache_dir: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS, "--bet", *(bet.label for bet in TRAINED_BETS),
        *_common(local_season_db, models, cache_dir), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + len(TRAINED_BETS) and lines[0] == ",".join(PREDICTION_COLUMNS)


def test_predictは出馬表の時点をオッズ無しで出し_題に出馬表と書く(local_season_db: Path, trained: tuple[Path, str], cache_dir: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", "--date", "2025-01-11", "--venue", "大井", "--race", "2", "--timing", "出馬表", "--bet", "単勝",
        *_common(local_season_db, models, cache_dir), "--format", "markdown",
    ])
    out = capsys.readouterr().out
    assert code == 0 and "出馬表の時点" in out and "木曜" not in out


def test_predictは速報の無いレースの当日に_取り込み方を案内して止まる(local_season_db: Path, trained: tuple[Path, str], cache_dir: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.PLAIN_CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS, "--bet", "単勝",
        *_common(local_season_db, models, cache_dir),
    ])
    assert code == 1 and "nvstore realtime" in capsys.readouterr().err


def test_predictは学習していない券種で_trainを案内する(local_season_db: Path, trained: tuple[Path, str], cache_dir: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS, "--bet", "馬連",
        *_common(local_season_db, models, cache_dir),
    ])
    assert code == 1 and "train" in capsys.readouterr().err
