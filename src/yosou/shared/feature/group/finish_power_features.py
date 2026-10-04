"""Q. 勝ち切る材料（10個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..feature_catalog import FINISH_POWER_NAMES

#: 出走の行と、材料の表を突き合わせる鍵（木曜は馬番が無いので、馬で突き合わせる）。
_KEY = ["race_id", "horse_id"]


class FinishPowerFeatures:
    """Q. 勝ち切る材料（名前は ``FINISH_POWER_NAMES``）。

    馬の近10走の1着数・2着数・勝ち切り率（1着 ÷ 連対）・惜敗数・勝ったときの着差の平均・人気で負けた数と、
    騎手と調教師の近1年の勝ち切り率と1番人気のときの勝率。3着以内に堅く来る力ではなく、勝ち切る力を表す材料で、
    近走と適性の予想の当日の1着のモデルだけが使う（3着以内のモデルに足しても確率の誤差は小さくならなかった。設計書 15 の 15）。
    元の記録は ``records.finish_records``（``FinishRecordsLoader`` が読む）。表に無い出走は欠損値。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        if records.finish_records.empty:
            return pd.DataFrame(float("nan"), index=entries.index, columns=list(FINISH_POWER_NAMES))
        keys = pd.DataFrame({"race_id": entries["race_id"].astype(str).to_numpy(), "horse_id": entries["horse_id"].astype(str).to_numpy()})
        table = records.finish_records.astype({"race_id": str, "horse_id": str}).drop_duplicates(_KEY)
        aligned = keys.merge(table, on=_KEY, how="left")
        return aligned[list(FINISH_POWER_NAMES)].astype("float64").set_axis(entries.index)
