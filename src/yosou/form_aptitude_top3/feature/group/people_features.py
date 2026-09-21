"""C. 騎手と調教師（6個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords
from ..history import Top3Rate

#: 事実表の列をそのまま使う特徴量（特徴量の名前 → 事実表の列）。騎手と調教師はコードで渡す。
_COPIED = EntryColumns({
    "騎手": "jockey_code", "騎手の減量": "apprentice", "乗り替わり": "jockey_change",
    "調教師": "trainer_code",
})


class PeopleFeatures:
    """C. 騎手と調教師。誰が乗り、誰が育てたかと、その人の近1年の成績。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        jockey_rate = Top3Rate(entries, "jockey_code").of(records.jockey_days)
        trainer_rate = Top3Rate(entries, "trainer_code").of(records.trainer_days)
        return _COPIED.select(entries).assign(**{
            "騎手の近1年の3着以内の割合": jockey_rate,
            "調教師の近1年の3着以内の割合": trainer_rate,
        })
