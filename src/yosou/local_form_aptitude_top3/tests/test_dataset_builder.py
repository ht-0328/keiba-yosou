"""学習データ・予測用データの作り方（設計書 06 の図1・07・08・09・10）。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db
from 共通.local_codes import LOCAL_CLASS_ORDER
from 合成DB import synth

from yosou.shared.dataset import TOP3, WIN, FinishPowerFreeData, PredictionData, TrainingData
from yosou.shared.dataset.column_names import FINISH
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository.career_count_sql import CareerCountSql
from yosou.shared.tests import local_season as season

from ..dataset import local_dataset_builder
from ..feature import CATALOG, LOCAL_BASE_FEATURES
from ..repository import LOCAL_CAREER_LAYOUT

#: 出馬表のレース（確定前なので DB にオッズが無い）に、手で渡す単勝オッズ。馬番が小さいほど人気。
CARD_ODDS: dict[int, float] = {horse_no: 1.5 + horse_no for horse_no in range(1, 9)}


def _prediction(path: Path, race_id: str, timing: PredictionTiming,
                odds: Mapping[int, float] | None = None) -> PredictionData:
    with db.open_db(path) as con:
        return local_dataset_builder(con).build_prediction_data(race_id, timing, odds=odds)


def test_catalog_has_the_designed_counts():
    # 土台 65個（調教を除く）と、時点ごとの数（設計書 07）。当日は Q を含めて 96個、3着以内のモデルには Q を外した 86個を渡す
    assert len(LOCAL_BASE_FEATURES) == 65 and not any(feature.group == "I" for feature in LOCAL_BASE_FEATURES)
    assert len(CATALOG.names) == 96
    assert len(CATALOG.columns_for(PredictionTiming.THURSDAY)) == 69
    assert len(CATALOG.columns_for(PredictionTiming.DAY_BEFORE)) == 78
    assert len(CATALOG.columns_for(PredictionTiming.RACE_DAY)) == 96
    # 枠番・馬番は出馬表から分かる（中央の木曜では分からない）
    assert {"枠番", "馬番"} <= set(CATALOG.columns_for(PredictionTiming.THURSDAY))
    assert not {"単勝オッズ", "馬場状態", "馬体重"} & set(CATALOG.columns_for(PredictionTiming.THURSDAY))


def test_career_layout_reads_columns_the_local_table_has():
    # 出走別着度数地方の欄の決めごとが読む列は、地方の表（合成DB も実DB と同じ列名）に全部ある
    needed = set(CareerCountSql("c", "t", LOCAL_CAREER_LAYOUT).source_columns())
    assert needed <= set(synth.ND_COLUMNS)
    assert LOCAL_CAREER_LAYOUT.table == "nd" and LOCAL_CAREER_LAYOUT.total_item == "総合着回数"


def test_training_data_is_the_local_season(training_data: TrainingData):
    assert training_data.ids["開催日"].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert list(training_data.features.columns) == list(CATALOG.names)
    assert set(training_data.features["競馬場"]) == {season.VENUE_NAME}
    assert set(training_data.features["芝ダ"]) == {"ダート"}
    # 所属は地方（東西所属コード 3）
    assert set(training_data.features["所属"]) == {"招待"}


def test_class_comes_from_the_condition_name(training_data: TrainingData):
    # Ｃ２・Ｂ２・Ｃ１・3歳の条件戦・重賞（グレード P）が、地方の並び順になる
    expected = {LOCAL_CLASS_ORDER[name] for name in ("C2", "B2", "C1", "年齢の条件戦", "重賞")}
    assert set(training_data.features["クラス"].dropna().astype(int)) == expected


def test_career_counts_come_from_nd(training_data: TrainingData):
    # 通算は総合着回数。全部のレースが大井のダートなので、同じ競馬場・芝ダでの通算と一致する
    assert training_data.features["通算の出走数"].notna().all()
    pd.testing.assert_series_equal(
        training_data.features["通算の出走数"], training_data.features["同じ競馬場・芝ダでの通算の出走数"], check_names=False,
    )


def test_targets_follow_the_final_finish(training_data: TrainingData):
    finish = training_data.evaluation[FINISH].astype("float64")
    assert (training_data.targets[TOP3] == finish.between(1, 3).astype(int)).all()
    assert (training_data.targets[WIN] == (finish == 1).astype(int)).all()


def test_finish_power_is_removed_for_the_top3_model(training_data: TrainingData):
    top3 = FinishPowerFreeData().training(training_data)
    assert len(top3.catalog.columns_for(PredictionTiming.RACE_DAY)) == 86


def test_entry_list_prediction_has_numbers_but_no_odds(local_season_db: Path):
    data = _prediction(local_season_db, season.PLAIN_CARD_RACE_ID, PredictionTiming.THURSDAY)
    assert len(data) == 8 and data.features["馬番"].notna().all()
    assert "単勝オッズ" not in data.features.columns and data.baseline is None


def test_day_before_prediction_uses_given_odds_and_announced_going(local_season_db: Path):
    data = _prediction(local_season_db, season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE, CARD_ODDS)
    # 速報で取消になった馬番8 は入らない。馬場状態は最後に発表された重
    assert len(data) == 7 and season.SCRATCHED_HORSE_NO not in set(data.ids["馬番"])
    assert set(data.features["馬場状態"]) == {"重"}
    assert data.features["人気順位"].min() == 1 and data.baseline is not None


def test_day_before_prediction_requires_odds(local_season_db: Path):
    with pytest.raises(ValueError, match="--odds"):
        _prediction(local_season_db, season.PLAIN_CARD_RACE_ID, PredictionTiming.DAY_BEFORE)
