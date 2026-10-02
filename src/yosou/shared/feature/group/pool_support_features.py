"""N. 券種ごとのオッズから見た支持（6個）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ...repository import POOLS
from ..entry_records import EntryRecords
from ..feature_catalog import POOL_SUPPORT_NAMES
from ..odds import TOP2_RATE, TOP3_RATE, WIN_RATE, MarketPlaces

#: 比べる単勝オッズ側の確率（Harville の式で勝率から2着以内率・3着以内率を出す）。
_MARKET_COLUMNS = {"勝率": WIN_RATE, "2着以内率": TOP2_RATE, "3着以内率": TOP3_RATE}
#: 対数にするときの下限（0 は対数にできない）。
_FLOOR = 1e-6
#: 出走の行と、券種オッズの表を突き合わせる鍵。
_KEY = ["race_id", "horse_no"]


class PoolSupportFeatures:
    """N. 券種ごとのオッズから見た支持（名前は ``POOL_SUPPORT_NAMES``）。

    log（券種のオッズから見た確率）− log（単勝オッズから見た確率）。

    例: 単勝から見た3着以内率 0.20 の馬が、3連複から見ると 0.26 なら、log(0.26 ÷ 0.20) ≒ +0.26。売上の大きい券種で
    単勝より高く評価されている馬を表す。研究「既存モデルの改善」の材料の実験で採用の基準を満たし、研究「一番人気を疑う」で
    ◎が1番人気を上回った。券種のオッズがそろうのは当日（締め切り前の速報オッズ 0B30 か、終わったレースの確定オッズ）。
    券種の確率は ``records.pool_probabilities``（``PoolProbabilityLoader`` が読む）。発売の無い券種・取り込んでいない馬は欠損値。
    custom_binary の「〜と単勝の差」と同じ値（複勝とワイドの確率の倍率の違いは、定数のずれだけ）。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        market = MarketPlaces().of(entries)
        pools = self._aligned(entries, records.pool_probabilities)
        ratios = {name: self._log_ratio(pools[spec.column], market[_MARKET_COLUMNS[spec.market]])
                  for spec, name in zip(POOLS, POOL_SUPPORT_NAMES)}
        return pd.DataFrame(ratios, index=entries.index)

    def _aligned(self, entries: pd.DataFrame, probabilities: pd.DataFrame) -> pd.DataFrame:
        """出走の行の並びにそろえた券種の確率。表が空（読んでいない）なら全部欠損値。"""
        columns = [spec.column for spec in POOLS]
        if probabilities.empty:
            return pd.DataFrame(np.nan, index=entries.index, columns=columns)
        keys = pd.MultiIndex.from_arrays([entries["race_id"].astype(str),
                                          pd.to_numeric(entries["horse_no"], errors="coerce")])
        table = probabilities.assign(race_id=probabilities["race_id"].astype(str),
                                     horse_no=pd.to_numeric(probabilities["horse_no"], errors="coerce"))
        aligned = table.drop_duplicates(_KEY).set_index(_KEY).reindex(columns=columns).reindex(keys)
        return aligned.set_axis(entries.index).astype("float64")

    def _log_ratio(self, pool: pd.Series, market: pd.Series) -> pd.Series:
        return np.log(pool.clip(lower=_FLOOR)) - np.log(market.astype("float64").clip(lower=_FLOOR))
