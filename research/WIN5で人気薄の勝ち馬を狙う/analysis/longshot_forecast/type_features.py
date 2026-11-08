"""出走の表（型の列つき）から、人気薄の1着の予想に足す「型の材料」の列を作る。どれもレースの前に分かる値。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..theory.runner_type_catalog import RUNNER_TYPES

#: 推定脚質・前走の脚質を数にするときの値（前ほど小さい）。
_STYLE_ORDER: dict[str, float] = {"逃げ": 1.0, "先行": 2.0, "差し": 3.0, "追込": 4.0}
#: 鍵の列（学習の表の ID 列の名前）。
RACE_ID, HORSE_NO = "レースID", "馬番"


@dataclass(frozen=True)
class TypeFeatures:
    """1行 = 1頭。列は鍵（レースID・馬番）と ``COLUMNS`` の型の材料。``runners`` は ``RunnerEnrichment`` と ``RunnerTypeFlags`` を通した表。"""

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        x = runners
        handicap = x["weight_type"] == "ハンデ"
        values = {
            "型_逃げ先行での3着内": x["front_places_before"],
            "型_差し追込での3着内": x["back_places_before"],
            "型_前と後ろの3着内の差": x["front_places_before"] - x["back_places_before"],
            "型_近5走の逃げ先行での3着内": x["recent_front_places"],
            "型_近5走の差し追込での3着内": x["recent_back_places"],
            "型_前走の脚質": x["prev_style"].map(_STYLE_ORDER),
            "型_推定脚質": x["style_before"].map(_STYLE_ORDER),
            "型_楽に前へ行ける": (x["style_before"].isin(["逃げ", "先行"]) & (x["lead_candidates"] <= 1)).astype(float),
            "型_同じ格以上での3着内の差": x["best_placed_class"] - x["class_order"],
            "型_同じ格以上での勝ちの差": x["best_win_class"] - x["class_order"],
            "型_前走との距離の差": (x["distance_m"] - x["prev_distance_m"]).abs(),
            "型_前走から馬場が替わった": (x["prev_condition"].notna() & (x["prev_condition"] != x["condition"])).astype(float),
            "型_前走からクラスが下がった幅": x["prev_class_order"] - x["class_order"],
            "型_ハンデの斤量差": x["carried_gap"].where(handicap, np.nan),
            "型_騎手の勝率の前走との差": x["jockey_rate"] - x["prev_jockey_rate"],
            "型_人気薄の市場合計": x["longshot_market"],
            "型_1番人気の単勝オッズ": x["favorite_odds"],
            **{f"型_{rule.name.split(' ')[0]}": x[rule.name].astype(float) for rule in RUNNER_TYPES},
        }
        keys = pd.DataFrame({RACE_ID: x["race_id"].astype(str), HORSE_NO: x["horse_no"].astype(int)})
        return pd.concat([keys, pd.DataFrame(values, index=x.index).astype(float)], axis=1).reset_index(drop=True)


#: 足す列の名前（``build`` の並び）。
COLUMNS: tuple[str, ...] = (
    "型_逃げ先行での3着内", "型_差し追込での3着内", "型_前と後ろの3着内の差", "型_近5走の逃げ先行での3着内", "型_近5走の差し追込での3着内",
    "型_前走の脚質", "型_推定脚質", "型_楽に前へ行ける", "型_同じ格以上での3着内の差", "型_同じ格以上での勝ちの差", "型_前走との距離の差",
    "型_前走から馬場が替わった", "型_前走からクラスが下がった幅", "型_ハンデの斤量差", "型_騎手の勝率の前走との差", "型_人気薄の市場合計",
    "型_1番人気の単勝オッズ", *(f"型_{rule.name.split(' ')[0]}" for rule in RUNNER_TYPES),
)
