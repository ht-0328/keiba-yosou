"""レースの中身（人気の偏り・モデルと市場の食い違い など）を、印を付けた予測の表から1行 = 1レースで作る。"""

from __future__ import annotations

import pandas as pd

#: レースの中身の列（docs/03 の 3）。どれも当日の発走前に分かる値（確定オッズで数える）。
TRAITS: dict[str, str] = {
    "favorite_odds": "1番人気の単勝オッズ",
    "top3_share": "市場の勝率の上位3頭の和",
    "field_size": "頭数",
    "model_gap": "モデルと市場の勝率の食い違い（差の絶対値の和の半分）",
    "top_value": "◎ の単勝の期待値",
    "has_danger": "危険な人気馬がいるか（1 か 0）",
}


class RaceTraits:
    """印を付けた予測の表（研究「複勝以外の回収率100超」の ``marked-<年>から.parquet``。1行 = 1頭）から、レースごとの中身の列 ``TRAITS`` を作る。

    使う列: ``race_id``・``win_odds``・``market_win``（オッズから見た勝率）・``win_probability``（モデルの勝率）・``field_size``・
    ``mark``・``win_value``・``is_danger``。例: 1番人気が 1.8倍、上位3頭の市場の勝率が 0.40・0.20・0.10 なら、favorite_odds 1.8・top3_share 0.70。
    """

    def of(self, marked: pd.DataFrame) -> pd.DataFrame:
        frame = marked.assign(race_id=marked["race_id"].astype(str))
        race = frame.groupby("race_id", sort=True)
        gap = (frame["win_probability"] - frame["market_win"]).abs().groupby(frame["race_id"]).sum() / 2.0
        top3 = race["market_win"].apply(lambda values: values.nlargest(3).sum())
        top_value = frame[frame["mark"] == "◎"].groupby("race_id")["win_value"].first()
        table = pd.DataFrame({
            "favorite_odds": race["win_odds"].min(), "top3_share": top3, "field_size": race["field_size"].first(),
            "model_gap": gap, "top_value": top_value, "has_danger": race["is_danger"].max().astype(float),
        })
        return table.reset_index()
