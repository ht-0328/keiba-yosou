"""予測の結果に足す、オッズから見た3着以内率と複勝の期待値の列。"""

from __future__ import annotations

import pandas as pd

from ..dataset import PredictionData
from ..feature.odds import TOP3_RATE
from .place_expected_value import PlaceExpectedValue
from .place_price_estimator import PlacePriceEstimator


class PlaceValueColumns:
    """3着以内を当てる予想（全頭・穴馬）の予測の結果に足す列を作る（既存モデルの修正計画の 1「来る確率と期待値を別々に」）。

    - オッズから見た3着以内率（基準）: オッズが分かる時点（前日・当日）だけ。
    - 複勝的中の確率・複勝の見込みの倍率・複勝の期待値: そのうえ、見込みの倍率（学習のときに保存したもの）があるときだけ。
    木曜（オッズが無い）は何も足さない。確率の順の並びはそのまま残し、買う候補は期待値で選べるようにする。
    """

    def __init__(self, estimator: PlacePriceEstimator | None) -> None:
        self._estimator = estimator

    def of(self, top3: pd.Series, data: PredictionData) -> pd.DataFrame:
        """行の並びと index は ``data.ids`` と同じ。複勝の期待値の材料は ``data.market``（複勝オッズ・頭数・オッズから見た率）。"""
        if data.baseline is None or data.market is None:
            return pd.DataFrame(index=data.ids.index)
        base = pd.DataFrame({TOP3_RATE: data.baseline.probabilities().to_numpy()}, index=data.ids.index)
        if self._estimator is None:
            return base
        values = PlaceExpectedValue(self._estimator).of(top3, data.market)
        return pd.concat([base, values], axis=1)
