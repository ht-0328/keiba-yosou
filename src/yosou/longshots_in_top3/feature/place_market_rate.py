"""複勝オッズから見た3着以内率を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

#: 複勝が2着までになる頭数の上限（7頭以下は2着まで。8頭以上は3着まで）。
_SMALL_FIELD_UP_TO = 7
#: 複勝で当たりになる頭数（少頭数・多頭数）。
_PLACES_IN_SMALL_FIELD, _PLACES_IN_LARGE_FIELD = 2, 3


class PlaceMarketRate:
    """出走の行（``race_id``・``place_odds_low``・``place_odds_high``）から、複勝オッズから見た3着以内率を出す。

    複勝の払戻は最低〜最高の幅でしか分からないので、その真ん中の逆数を「支持の強さ」とし、同じレースの中で
    合計が当たりの頭数（8頭以上は 3、7頭以下は 2）になるようにそろえる。1 を超えた値は 1 にする。
    例: 8頭立てで真ん中のオッズが 2.0倍・4.0倍・… なら、逆数 0.5・0.25・… を合計 3 になるよう伸び縮みさせる。
    複勝オッズの無い馬（木曜・無投票・複勝を売らない4頭以下のレース）は欠損値で、そろえる合計にも入れない。
    頭数は、行の中の同じレースの馬の数（出走した馬の数）。
    """

    def of(self, entries: pd.DataFrame) -> pd.Series:
        """行の並びと index は ``entries`` と同じ。"""
        middle = (as_numbers(entries["place_odds_low"]) + as_numbers(entries["place_odds_high"])) / 2.0
        support = 1.0 / middle.where(middle > 0)
        race_ids = entries["race_id"]
        total = support.groupby(race_ids).transform("sum")
        field_size = race_ids.groupby(race_ids).transform("size")
        places = np.where(field_size <= _SMALL_FIELD_UP_TO, _PLACES_IN_SMALL_FIELD, _PLACES_IN_LARGE_FIELD)
        rate = support / total.where(total > 0) * places
        return rate.clip(upper=1.0)
