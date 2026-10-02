"""出どころごとの確率の当たり具合。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest import TOTAL_LABEL

#: 確率をログにするときの端の丸め。
_EDGE = 1e-6


class SourceLogLoss:
    """出どころごとの確率が「3着以内（複勝の対象着順以内）」をどれだけ当てるかを、年ごとのログ損失で出す。小さいほど良い。

    回収率は買い目の選び方で揺れるので、確率そのものの当たり具合も横に置く。最後の行は全期間。
    """

    def by_year(self, table: pd.DataFrame, sources: tuple[str, ...]) -> pd.DataFrame:
        rows = [self._row(int(year), group, sources) for year, group in table.groupby("year")]
        rows.append(self._row(TOTAL_LABEL, table, sources))
        return pd.DataFrame(rows)

    def _row(self, label: object, group: pd.DataFrame, sources: tuple[str, ...]) -> dict[str, object]:
        row: dict[str, object] = {"年": label, "頭数": len(group)}
        for source in sources:
            row[source] = round(self._log_loss(group[source], group["placed"]), 5)
        return row

    def _log_loss(self, probability: pd.Series, placed: pd.Series) -> float:
        p = probability.clip(_EDGE, 1 - _EDGE).to_numpy(dtype=float)
        y = placed.to_numpy(dtype=float)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
