"""レース単位の展開の手がかりと、今回の馬の条件を数にした列を作る。"""

from __future__ import annotations

import pandas as pd

#: 所属が栗東か（坂路のタイムは美浦と栗東でコースが違うので、所属を一緒に渡す）。
_RITTO = "栗東"


class RaceLevelColumns:
    """``RACE_LEVEL_COLUMNS`` の8個（ability_columns.py）。

    - 先頭率の合計: 同じレースの馬の、近5走で最初のコーナーを先頭で回った割合の合計（逃げたい馬がどれだけいるか）
    - ほかの馬の先頭率の合計: その合計から自分の分を引いた値
    - 馬番の位置: 馬番 ÷ 頭数（木曜は馬番が無いので欠損値）
    - ハンデ戦・所属_栗東・ブリンカーあり・減量騎手: そうなら 1。競馬場コード: 競馬場コードの数
    ``table`` は先頭率_近5走・horse_no・weight_type・venue_code・affiliation・blinker・apprentice を持つ行。
    """

    def build(self, table: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``table`` と同じ。"""
        lead = table["先頭率_近5走"].astype(float).fillna(0.0)
        total = lead.groupby(table["race_id"]).transform("sum")
        runners = table.groupby("race_id")["race_id"].transform("size")
        return pd.DataFrame({
            "先頭率の合計": total, "ほかの馬の先頭率の合計": total - lead,
            "馬番の位置": pd.to_numeric(table["horse_no"], errors="coerce") / runners,
            "ハンデ戦": (table["weight_type"] == "ハンデ").astype(float),
            "競馬場コード": pd.to_numeric(table["venue_code"], errors="coerce"),
            "所属_栗東": (table["affiliation"] == _RITTO).astype(float),
            "ブリンカーあり": (table["blinker"] == "あり").astype(float),
            "減量騎手": (table["apprentice"] == "減量あり").astype(float),
        }, index=table.index)
