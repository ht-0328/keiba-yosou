"""1通りの設定で custom_binary のモデルを学び、確かめる期間で買い方を選び、テスト期間で1回だけ確かめる。"""

import time

import pandas as pd

from yosou.custom_binary import workflow
from yosou.custom_binary.dataset import select_training_data
from yosou.custom_binary.feature.registry import FeatureRegistry

from .feature_table import FeatureTable
from .model_config import ModelConfig
from .search_periods import SearchPeriods

#: 確かめる期間で買い方を選ぶときの、最低の点数（少なすぎる買い方は偶然で回収率が高く出る）。
MIN_CONFIRM_BETS = 100


class ModelTrial:
    def __init__(self, table: FeatureTable, registry: FeatureRegistry, periods: SearchPeriods) -> None:
        self._table = table
        self._registry = registry
        self._periods = periods

    def run(self, config: ModelConfig) -> dict:
        started = time.time()
        settings = config.settings(self._registry, self._periods)
        data = select_training_data(self._table.rows, self._table.frame, settings, self._registry.catalog(settings.selected))
        ensemble, train, valid = workflow.fit(data, settings)
        test = data.between(self._periods.test_from, None)
        confirm = workflow.report(ensemble, valid, config.target, train)
        final = workflow.report(ensemble, test, config.target, train)
        chosen = choose(confirm["paybacks"], config.bet, config.value_lines_only)
        tested = next(row for row in final["paybacks"] if row["買い方"] == chosen["買い方"]) if chosen else None
        return {
            "設定": config.yaml_values(), "特徴量": list(config.features), "券種": config.bet,
            "確かめる期間": confirm, "テスト期間": final, "選んだ買い方": chosen, "テストでの結果": tested,
            "秒": round(time.time() - started),
        }


#: 期待値の線だけから選ぶときの候補（計画で、テスト期間を見る前に決めた範囲）。
VALUE_LINES = ("期待値1以上", "期待値1.1以上", "期待値1.2以上", "期待値1.3以上", "期待値1.5以上")


def choose(paybacks: list[dict], bet: str, value_lines_only: bool = False) -> dict | None:
    """確かめる期間で、その券種の回収率がいちばん高い買い方（モデルなしの全頭買いは除く）。

    ``value_lines_only`` なら、期待値 1.0〜1.5 の線の中から選ぶ。
    """
    rows = pd.DataFrame(paybacks)
    rows = rows[(rows["点数"] >= MIN_CONFIRM_BETS) & (rows["買い方"] != "対象の全頭（モデルなし）")]
    if value_lines_only:
        rows = rows[rows["買い方"].isin(VALUE_LINES)]
    if rows.empty:
        return None
    return rows.sort_values(f"{bet}回収率", ascending=False).iloc[0].to_dict()
