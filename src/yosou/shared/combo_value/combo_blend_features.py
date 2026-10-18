"""1つの券種の全部の組に、組の確率を作る4つのもと（の対数）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..betting import TicketType
from .combo_columns import horse_columns, split_combo
from .horse_strength import TOP3_RATIO, WIN_RATIO
from .trifecta_sources import HARVILLE, MARKET

#: 4つのもとの列（``WEIGHT_NAMES`` と同じ順）。
FEATURE_COLUMNS: tuple[str, ...] = ("log_own", "log_trifecta", "log_harville", "log_ratio")
#: ワイドは1レースで3組当たるので、市場の確率の合計を 3 にそろえる。
WIDE_WINNERS = 3.0
#: 対数を取る前の下限（確率 0 の組で -∞ にならないように）。
_FLOOR = 1e-9


class ComboBlendFeatures:
    """その券種のオッズの板（列 ``race_id``・``combo``・``odds``。ワイドは最低オッズ）と、3連単から足し合わせた確率（``PoolFolding.fold``）と、
    馬ごとの見立て（``HorseStrength.of``）から、1行 = 1組の表を作る。

    - ``log_own``: その券種のオッズの逆数をレースで合計 1（ワイドは 3）にそろえた値の対数。
    - ``log_trifecta``・``log_harville``: 3連単の市場・モデルの Harville から足し合わせた確率の対数。
    - ``log_ratio``: 組の各馬の「モデル ÷ 市場」の比の積の対数（馬単・3連単の1頭目は1着の比、ほかは3着以内の比）。
    オッズの無い組（無投票・取消）と、3連単から作れない組・比の無い馬を含む組は落とす。
    列は ``race_id``・``combo``・``h1``…・``odds`` と ``FEATURE_COLUMNS``。
    """

    def build(self, ticket_type: TicketType, board: pd.DataFrame, folded: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
        count = ticket_type.spec.horse_count
        names = horse_columns(count)
        rows = split_combo(board[board["odds"] > 0].assign(race_id=board["race_id"].astype(str)), count)
        inverse = 1.0 / rows["odds"]
        rows["own"] = inverse / inverse.groupby(rows["race_id"]).transform("sum") * (WIDE_WINNERS if ticket_type is TicketType.WIDE else 1.0)
        rows = rows.merge(folded.assign(race_id=folded["race_id"].astype(str)), on=["race_id", *names], how="inner")
        rows["log_ratio"] = self._log_ratio(ticket_type, rows, strength)
        rows["log_own"] = np.log(rows["own"].clip(lower=_FLOOR))
        rows["log_trifecta"] = np.log(rows[MARKET].clip(lower=_FLOOR))
        rows["log_harville"] = np.log(rows[HARVILLE].clip(lower=_FLOOR))
        rows = rows.dropna(subset=list(FEATURE_COLUMNS))
        return rows[["race_id", "combo", *names, "odds", *FEATURE_COLUMNS]].reset_index(drop=True)

    def _log_ratio(self, ticket_type: TicketType, rows: pd.DataFrame, strength: pd.DataFrame) -> pd.Series:
        table = strength.set_index(["race_id", "horse_no"])
        total = pd.Series(0.0, index=rows.index)
        for at, name in enumerate(horse_columns(ticket_type.spec.horse_count)):
            found = table.reindex(pd.MultiIndex.from_arrays([rows["race_id"], rows[name].astype(int)]))
            column = WIN_RATIO if ticket_type.spec.is_ordered and at == 0 else TOP3_RATIO
            total = total + np.log(found[column].to_numpy(dtype=float))
        return total
