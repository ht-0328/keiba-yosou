"""予測の流れを進める。"""

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput, OddsResolver, PopularityApplier, PopularityInput, PredictionData
from yosou.shared.repository import AnnouncedOddsRepository

from ..dataset import CustomDataset
from ..evaluation import PredictionValues
from ..feature.registry import FeatureRegistry
from .loaded_model import LoadedModel


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 人気を決める → 予測用データを作る → 2つのモデルの確率の平均を出す →
    今のオッズと複勝の想定払戻倍率から期待値を足す → 確率の高い順に並べる。
    開いた元DB を受け取る。何レースも続けて予想するときは、DB とモデルを1回だけ開いて使い回す。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, registry: FeatureRegistry) -> None:
        self._con = con
        self._registry = registry

    def run(self, race_id: str, model: LoadedModel,
            pops: list[str] | None = None, odds: list[str] | None = None) -> pd.DataFrame:
        """1レースの、対象の馬ごとの確率と期待値（確率の高い順）。対象の馬がいなければ 0行。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名・使用した人気）、``<目的>の確率``、期待値とその材料。
        ``pops``・``odds`` は利用者が ``--pops``・``--odds`` で渡した値（省略すると、元DB から決める）。
        """
        repository = AnnouncedOddsRepository(self._con)
        prices = OddsResolver(repository).resolve(race_id, OddsInput.of(odds) if odds is not None else None)
        popularity = PopularityApplier(repository).resolve(
            race_id, PopularityInput.of(pops) if pops is not None else None, prices,
        )
        data = CustomDataset(self._con, model.settings, self._registry).prediction(race_id, popularity, prices)
        name = self.probability_name(model)
        result = data.ids.copy()
        result[name] = model.ensemble.predict_proba(data) if len(data) else []
        result = self._with_values(result, data, model) if len(data) else result
        return result.sort_values(name, ascending=False, kind="stable")

    def probability_name(self, model: LoadedModel) -> str:
        """結果の、確率の列の名前（例: 馬券内の確率）。"""
        return f"{model.settings.target}の確率"

    def _with_values(self, result: pd.DataFrame, data: PredictionData, model: LoadedModel) -> pd.DataFrame:
        probability = result[self.probability_name(model)].to_numpy()
        values = PredictionValues().of(probability, model.settings.target, data.market, model.place_price)
        return result.join(values)
