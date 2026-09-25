"""券種オッズから見た確率と、単勝オッズから見た確率の食い違い。"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE, WIN_RATE, MarketPlaces

from ..repository import PoolSpec

#: 比べる単勝オッズ側の確率（Harville の式で勝率から2着以内率・3着以内率を出す）。
MARKET_COLUMNS = {"勝率": WIN_RATE, "2着以内率": TOP2_RATE, "3着以内率": TOP3_RATE}
#: 対数にするときの下限（0 は対数にできない）。
FLOOR = 1e-6


class PoolGap:
    """log（券種オッズから見た確率）− log（単勝オッズから見た確率）。

    プラスなら、その券種のプールは単勝より高く見ている。例: 3連複 0.14、単勝から見た3着以内率 0.08 なら
    log(0.14) − log(0.08) ≒ +0.56。売上の大きいプールのほうが正しければ、単勝・複勝が割安な向きを指す。
    単勝オッズ側の確率は、同じレースの全頭の単勝オッズから作る（人気範囲・条件で絞る前）。
    """

    kind = FeatureKind.NUMERIC
    known_from = PredictionTiming.RACE_DAY
    sources: tuple[str, ...] = ()

    def __init__(self, spec: PoolSpec) -> None:
        self.spec = spec
        self.name = f"{spec.name}と単勝の差"
        self.description = f"log({spec.name}) − log(単勝オッズから見た{spec.market})"
        self.dependencies = (spec.name,)

    def compute(self, records: EntryRecords, dependencies: Mapping[str, pd.Series]) -> pd.Series:
        market = MarketPlaces().of(records.entries)[MARKET_COLUMNS[self.spec.market]]
        pool = dependencies[self.spec.name]
        return np.log(pool.clip(lower=FLOOR)) - np.log(market.astype("float64").clip(lower=FLOOR))
