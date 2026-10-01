"""1つの設定の1年ぶん: その年より前で学習し直し、直前の1年で線を選び、その年の買い目の候補を出す。"""

import pandas as pd

from yosou.custom_binary.dataset import TrainingDataSelector
from yosou.custom_binary.evaluation import ExpectedValue, Paybacks, PlacePriceFit
from yosou.custom_binary.evaluation.payback_rules import EXPECTED_VALUE_LINES
from yosou.custom_binary.feature.registry import FeatureRegistry
from yosou.custom_binary.workflow import EnsembleFitter
from yosou.shared.dataset.column_names import PLACE_PAYOUT, RACE_DATE
from yosou.shared.feature.value_types import as_numbers

from .feature_table import FeatureTable
from .model_config import ModelConfig
from .model_trial import VALUE_LINES, choose
from .walk_forward_years import YearPeriods

#: 買い方の名前（例: 期待値1.2以上）から、線の値へ。
LINE_OF_NAME = {f"期待値{line:g}以上": line for line in EXPECTED_VALUE_LINES}
#: 残す買い目の候補の、期待値の下限（試す線でいちばん低いもの）。これより低い馬はどの線でも買わない。
LOWEST_LINE = min(LINE_OF_NAME[name] for name in VALUE_LINES)


class WalkForwardTrial:
    """線は、確かめる期間（予測する年の直前の1年）の成績だけで選ぶ。決まりは元の探索と同じ ``choose``。

    返す ``tickets`` は、予測した年の、期待値が ``LOWEST_LINE`` 以上の馬（1行 = 複勝1点）。
    列は day（開催日）・ev（期待値）・payout（100円あたりの複勝の払戻）。線を当てるのは後の集計で行う。
    """

    def __init__(self, table: FeatureTable, registry: FeatureRegistry) -> None:
        self._table = table
        self._registry = registry

    def run(self, config: ModelConfig, split: YearPeriods) -> dict:
        settings = config.settings(self._registry, split.periods)
        data = TrainingDataSelector().select(
            self._table.rows, self._table.frame, settings, self._registry.catalog(settings.selected),
        )
        ensemble, train, valid = EnsembleFitter().fit(data, settings)
        place_price = PlacePriceFit().fit(train)
        confirm = Paybacks().of(valid, ensemble.predict_proba(valid), config.target, place_price)
        chosen = choose(confirm, config.bet, config.value_lines_only)
        test = data.between(split.periods.test_from, split.test_until)
        value = ExpectedValue().of(test, ensemble.predict_proba(test), config.target, place_price)
        tickets = pd.DataFrame({
            "day": test.ids[RACE_DATE].to_numpy(), "ev": value,
            "payout": as_numbers(test.evaluation[PLACE_PAYOUT]).fillna(0).to_numpy(),
        })
        return {
            "year": split.year, "line": LINE_OF_NAME[chosen["買い方"]] if chosen else None,
            "confirm": chosen, "runners": len(test), "tickets": tickets[tickets["ev"] >= LOWEST_LINE].reset_index(drop=True),
        }
