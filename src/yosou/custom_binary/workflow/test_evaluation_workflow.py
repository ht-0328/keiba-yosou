"""テスト期間の評価の流れを進める。"""

from pathlib import Path

from 共通 import db

from ..dataset import CustomDataset
from ..evaluation import HISTORICAL_NOTE, ModelReport
from ..feature.registry import FeatureRegistry
from ..store import ModelStore


class TestEvaluationWorkflow:
    """テスト期間の評価の流れ（設計書 05 の「テスト期間の評価」）。

    保存したモデルと設定を読む → 学習と同じ学習データを作る → テスト期間の行だけで当たり具合と回収率を出す →
    モデルのフォルダに ``test_evaluation.json`` を書く。複勝の想定払戻倍率は、学習期間の払戻から求める。
    """

    #: pytest がテストのクラスと取り違えないようにする（名前が Test で始まるため）。
    __test__ = False

    def __init__(self, registry: FeatureRegistry, database: Path | None = None) -> None:
        self._registry = registry
        self._database = database

    def run(self, models: Path) -> dict:
        """テスト期間の成績（``scores`` と ``paybacks``）を返す。"""
        store = ModelStore(models)
        settings, ensemble = store.load(self._registry)
        with db.open_db(self._database) as con:
            data = CustomDataset(con, settings, self._registry).training()
        test = data.between(settings.period.test_first_day, None)
        train = data.between(settings.period.train_first_day, settings.period.valid_first_day)
        result = ModelReport().of(ensemble, test, settings.target, train)
        store.save_test_evaluation({
            "test_from": settings.period.test_first_day.isoformat(), "note": HISTORICAL_NOTE, **result,
        })
        return result
