"""今のモデルの1着の確率の人気薄の分を、人気薄の1着の予想の確率に置き換え、レースの中で合計 1 にそろえた予測を作る（docs/03 の 1.2 の「出力の使い方」）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .longshot_variant import LONGSHOT_FROM

#: 書く予測の表の列（研究「既存モデルの改善」の予測の表と同じ名前。道具「印の成績」の ``PredictionFile`` で読める）。
_OUT_COLUMNS: dict[str, str] = {
    "race_id": "レースID", "race_date": "開催日", "horse_id": "馬ID", "horse_no": "馬番", "share": "確率",
    "fold": "区切り", "period": "期間", "segment": "区分",
}
#: 人気薄の確率の合計の上限（今のモデルの人気馬の分が無くならないように）。
_MAX_LONGSHOT_TOTAL = 0.9


@dataclass(frozen=True)
class CombinedWinShare:
    """``current`` は今のモデルの区切りごとの予測（``PredictionFile.load`` の表）、``longshot`` は人気薄の1着の予想の予測（レースID・馬番・確率・人気）。

    人気薄（``longshot_from`` 番人気以下）の馬は人気薄の予想の確率をそのまま使い、ほかの馬は今のモデルのそろえた確率の比を保って、
    残り（1 − 人気薄の合計）に縮める。人気薄の予想の無いレースは、今のモデルのそろえた確率のまま。"""

    longshot_from: int = LONGSHOT_FROM

    def combine(self, current: pd.DataFrame, longshot: pd.DataFrame) -> pd.DataFrame:
        frame = current.copy()
        frame["horse_no"] = frame["horse_no"].astype(int)
        frame["share"] = frame["probability"] / frame.groupby("race_id")["probability"].transform("sum")
        chosen = longshot.loc[longshot["人気"] >= self.longshot_from, ["レースID", "馬番", "確率"]]
        chosen = chosen.rename(columns={"レースID": "race_id", "馬番": "horse_no", "確率": "longshot"})
        frame = frame.merge(chosen.astype({"race_id": str, "horse_no": int}), on=["race_id", "horse_no"], how="left")
        replaced = frame["longshot"].notna()
        race = frame["race_id"]
        longshot_total = frame["longshot"].fillna(0.0).groupby(race).transform("sum")
        scale = (longshot_total.clip(upper=_MAX_LONGSHOT_TOTAL) / longshot_total).where(longshot_total > 0, 1.0)
        others = frame["share"].where(~replaced, 0.0).groupby(race).transform("sum")
        frame["share"] = (frame["longshot"] * scale).where(replaced, frame["share"] * (1.0 - longshot_total * scale) / others)
        return frame[list(_OUT_COLUMNS)].rename(columns=_OUT_COLUMNS)
