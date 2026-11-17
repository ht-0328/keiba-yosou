"""LateModels（2つのモデル）と LateModelStore（保存と読み出し）のテスト。小さな架空の表で学ぶ。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_features import LateFeatures
from 地方の直前の買い目.late_model_store import LateModelStore
from 地方の直前の買い目.late_models import LateModels
from 地方の直前の買い目.late_targets import LateTargets

from 地方の直前の買い目.testing.late_samples import material


@pytest.fixture(scope="module")
def rows():
    return LateTargets().attach(LateFeatures().build(material(races=150, heads=8)))


@pytest.fixture(scope="module")
def models(rows) -> LateModels:
    return LateModels.fit(rows, seeds=(1, 2))


def test_種の数だけ学び_買う馬らしさは0から1の間(rows, models: LateModels) -> None:
    scored = models.score(rows)
    assert len(models.likeness) == 2 and len(models.payback) == 2
    assert scored[c.LIKENESS].between(0, 1).all() and scored[c.PAYBACK].notna().all()


def test_同じ種なら同じ値(rows, models: LateModels) -> None:
    again = LateModels.fit(rows, seeds=(1, 2)).score(rows)
    assert np.allclose(again[c.LIKENESS], models.score(rows)[c.LIKENESS])


def test_保存して読み直すと同じ値_条件も読める(tmp_path: Path, rows, models: LateModels) -> None:
    store = LateModelStore(tmp_path / "models")
    store.save(models, {"レース数": 150})
    loaded = store.load()
    assert np.allclose(loaded.score(rows)[c.PAYBACK], models.score(rows)[c.PAYBACK])
    assert store.meta() == {"レース数": 150}


def test_モデルが無ければ_FileNotFoundError(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="fit.py"):
        LateModelStore(tmp_path / "無い").load()
