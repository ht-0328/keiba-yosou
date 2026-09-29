"""複勝の想定払戻倍率を、学習期間の払戻から求める。"""

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT
from yosou.shared.place_value import PlacePriceEstimator


class PlacePriceFit:
    """オッズ帯ごとの倍率を、``train``（学習期間）の払戻から求める（評価する期間の払戻は使わない）。"""

    def fit(self, train: TrainingData) -> PlacePriceEstimator:
        return PlacePriceEstimator().fit(train.evaluation[PLACE_ODDS_LOW], train.evaluation[PLACE_PAYOUT])
