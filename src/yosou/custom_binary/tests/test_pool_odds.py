from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from 共通 import db, keys
from 合成DB import synth
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..dataset import CustomDataset
from ..extra_data import ExtraDataLoader, PoolProbabilitySource
from ..extra_data.extra_data_loader import race_relation
from ..feature.builder import SelectedFeatureBuilder
from ..feature.pool_gap import PoolGap
from ..feature.registrations import default_registry
from ..repository import POOLS
from .test_workflow import POPS, settings  # noqa: F401  （フィクスチャ）

SPECS = {spec.column: spec for spec in POOLS}


@pytest.fixture
def pool_db(tmp_path):
    """5頭が走る1レースに、券種オッズ（確定の断面と、それより古い締め切り前の断面）を入れた合成DB。"""
    sample = synth.simple_race()
    ra = sample.ra[0]
    early = "04061000"
    sample.odds += [
        ("o6", synth.odds_header(ra, "o6")),
        ("o6", synth.odds_header(ra, "o6", stage="1", announced=early)),
        # 確定: 1/10 + 1/20 + 1/40 = 0.175。1着の馬ごとに 0.1, 0.05, 0.025 を足す。無投票（0）は数えない。
        ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "010203", 100)),
        ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "020103", 200, seq=2)),
        ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "040102", 400, seq=3)),
        ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "030102", 0, seq=4)),
        # 締め切り前の断面は、確定があれば使わない。
        ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "030102", 10, announced=early)),
        ("o5", synth.odds_header(ra, "o5")),
        ("o5__3連複オッズ", synth.odds_row(ra, "o5__3連複オッズ", "010203", 50)),
        ("o5__3連複オッズ", synth.odds_row(ra, "o5__3連複オッズ", "010204", 100, seq=2)),
        ("o1", synth.odds_header(ra, "o1")),
        *[("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", f"{num:02d}", low, high, seq=num))
          for num, (low, high) in {1: (10, 12), 2: (15, 19), 3: (20, 30), 4: (30, 50)}.items()],
        ("o3", synth.odds_header(ra, "o3")),
        ("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0102", 10, 14)),
        ("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0304", 30, 50, seq=2)),
    ]
    path = synth.build_db(tmp_path / "pool.duckdb", sample)
    return path, "".join(ra[name] for name in keys.RACE_KEY)


def test_pool_probabilities_by_hand(pool_db):
    path, race_id = pool_db
    with db.open_db(path) as con:
        values = PoolProbabilitySource().read(con, race_relation(race_id)).set_index("horse_no").sort_index()
    win = values["pool_trifecta_win"].dropna()
    assert win.to_dict() == pytest.approx({1: 0.1 / 0.175, 2: 0.05 / 0.175, 4: 0.025 / 0.175})
    trio = values["pool_trio_top3"]
    assert trio.to_dict() == pytest.approx({1: 1.0, 2: 1.0, 3: 0.2 / 0.3, 4: 0.1 / 0.3})
    # 複勝・ワイドは、レース内の合計が3（3着以内に入る頭数）になるようにしてある。
    assert values["pool_place_top3"].sum() == pytest.approx(3.0)
    assert values["pool_wide_top3"].sum() == pytest.approx(3.0)
    # 発売の無い券種（この合成DB では馬単・馬連）は欠損値。
    assert values["pool_exacta_win"].isna().all() and values["pool_quinella_top2"].isna().all()


def test_attach_keeps_rows_and_index(pool_db):
    path, race_id = pool_db
    entries = pd.DataFrame({"race_id": [race_id] * 3 + ["9999"], "horse_no": [4, 1, None, 1]}, index=[30, 10, 20, 40])
    with db.open_db(path) as con:
        attached = ExtraDataLoader(con).attach(entries, race_relation(race_id), ("券種オッズ",))
    assert attached.index.tolist() == [30, 10, 20, 40]
    assert attached["pool_trio_top3"].iloc[:2].tolist() == pytest.approx([0.1 / 0.3, 1.0])
    assert attached["pool_trio_top3"].iloc[2:].isna().all()  # 馬番の無い行・ほかのレースは欠損値


def test_unknown_source_and_bad_race_id():
    with pytest.raises(ValueError, match="未登録"):
        ExtraDataLoader(None).attach(pd.DataFrame({"race_id": [], "horse_no": []}), "(SELECT 1)", ("なし",))
    with pytest.raises(ValueError, match="数字"):
        race_relation("1' OR '1'='1")


def test_sources_are_read_only_when_needed():
    registry = default_registry()
    assert SelectedFeatureBuilder(registry, ("馬齢",), PredictionTiming.RACE_DAY).sources == ()
    # 単勝との差は、依存する券種の確率を通して元データを使う。
    gap = SelectedFeatureBuilder(registry, ("3連複から見た3着以内率と単勝の差",), PredictionTiming.RACE_DAY)
    assert gap.sources == ("券種オッズ",)
    assert gap.order == ("3連複から見た3着以内率", "3連複から見た3着以内率と単勝の差")
    with pytest.raises(ValueError, match="使えない"):
        SelectedFeatureBuilder(registry, ("3連単から見た勝率",), PredictionTiming.DAY_BEFORE)


def test_pool_feature_names_are_listed():
    names = set(default_registry().definitions)
    for spec in POOLS:
        assert {spec.name, f"{spec.name}と単勝の差"} <= names


def test_gap_is_log_difference_from_win_odds_market():
    spec = SPECS["pool_trifecta_win"]
    entries = pd.DataFrame({"race_id": ["a", "a"], "win_odds": [2.0, 2.0]})
    pool = pd.Series([0.6, 0.4])
    gap = PoolGap(spec).compute(SimpleNamespace(entries=entries), {spec.name: pool})
    # 単勝から見た勝率はどちらも 0.5。
    assert gap.tolist() == pytest.approx([np.log(0.6 / 0.5), np.log(0.4 / 0.5)])


def test_missing_pool_odds_in_training_and_prediction(season_db, settings):
    registry = default_registry()
    selected = ("馬齢", "3連単から見た勝率", "3連単から見た勝率と単勝の差")
    pool_settings = replace(settings, selected=selected)
    pops = {int(pair.split(":")[0]): int(pair.split(":")[1]) for pair in POPS}
    with db.open_db(season_db) as con:
        dataset = CustomDataset(con, pool_settings, registry)
        data = dataset.training()
        assert list(data.features.columns) == list(selected)
        assert data.features["3連単から見た勝率"].isna().all()  # 合成のシーズンには券種オッズが無い
        with pytest.raises(ValueError, match="券種オッズが未取得"):
            dataset.prediction(season.CARD_RACE_ID, pops)
