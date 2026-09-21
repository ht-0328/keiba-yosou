"""H. 血統（6個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords
from ..history import PedigreeTop3Rate

#: 名前をそのまま使う特徴量（特徴量の名前 → 事実表の列）。
_COPIED = EntryColumns({"父": "sire", "父の父": "grandsire", "母の父": "damsire"})


class PedigreeFeatures:
    """H. 血統。名前そのものと、産駒の近1年の成績（力と、芝ダの適性）。

    産駒の成績は、その血統を持つ馬たちが走った成績で、種牡馬自身が現役だったころの成績ではない。
    距離帯別・競馬場別の成績は入れない。翌年まで続かない（たまたまの差である）ことを確かめたため。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        sire_rate = PedigreeTop3Rate(entries, "sire")
        damsire_rate = PedigreeTop3Rate(entries, "damsire")
        return _COPIED.select(entries).assign(**{
            "父の産駒の近1年の3着以内の割合": sire_rate.of_all_surfaces(records.sire_days),
            "父の産駒の同じ芝ダでの近1年の3着以内の割合": sire_rate.of_same_surface(records.sire_days),
            "母の父の産駒の近1年の3着以内の割合": damsire_rate.of_all_surfaces(records.damsire_days),
        })
