"""勝った人気薄を見て作った「馬の側の型」。どれもレースの前に分かる値だけで決める。1頭が複数の型に当てはまってよい。"""

from __future__ import annotations

import pandas as pd

from .flag_rule import FlagRule

#: 「前の走で負けた」とみなす着順。
_BEATEN = 6
#: 「条件が違う」とみなす距離の差（m）。
_DISTANCE_GAP = 400
#: 「上の騎手」とみなす前の年の勝率の差。
_JOCKEY_GAP = 0.03
#: 「ハンデで軽い」とみなす、レースの平均との斤量の差（kg）。
_LIGHT = -1.0


def _condition_differed(x: pd.DataFrame) -> pd.Series:
    """前の走が今回と違う条件だったか（芝ダ・400m 以上の距離・重〜不良と良の入れ替わり・上のクラス）。"""
    surface = x["surface_change"].isin(["芝→ダート", "ダート→芝"])
    distance = (x["distance_m"] - x["prev_distance_m"]).abs() >= _DISTANCE_GAP
    heavy_to_good = x["prev_condition"].isin(["重", "不良"]) & (x["condition"] == "良")
    good_to_heavy = (x["prev_condition"] == "良") & x["condition"].isin(["重", "不良"])
    higher_class = x["prev_class_order"] > x["class_order"]
    return surface | distance | heavy_to_good | good_to_heavy | higher_class


RUNNER_TYPES: tuple[FlagRule, ...] = (
    FlagRule("A 力の見直し", "実績", "今回と同じかそれより上のクラスで3着以内に入ったことがあるのに、前の走は6着以下（近走だけで見限られた）",
             lambda x: (x["best_placed_class"] >= x["class_order"]) & (x["prev_finish"] >= _BEATEN)),
    FlagRule("B 前走は条件が合わなかった", "条件替わり",
             "前の走は6着以下で、前の走は今回と条件が違い（芝ダ・400m 以上の距離・重〜不良と良・上のクラス）、今回の芝ダで3着以内の実績がある",
             lambda x: (x["prev_finish"] >= _BEATEN) & _condition_differed(x) & (x["surface_places_before"] >= 1)),
    FlagRule("C 先行できる展開", "枠と展開", "推定脚質が逃げか先行で、レースの逃げ候補が1頭以下（楽に前へ行ける）",
             lambda x: x["style_before"].isin(["逃げ", "先行"]) & (x["lead_candidates"] <= 1)),
    FlagRule("D 近走が良いのに人気が無い", "前走", "前の走で3着以内か、5着以内で勝ち馬とのタイム差 0.5秒以内（昇級などで人気が付ききらない）",
             lambda x: (x["prev_finish"] <= 3) | ((x["prev_finish"] <= 5) & (x["prev_time_diff"] <= 0.5))),
    FlagRule("E ハンデで軽い", "斤量", "ハンデ戦で、斤量がレースの平均より 1kg 以上軽い",
             lambda x: (x["weight_type"] == "ハンデ") & (x["carried_gap"] <= _LIGHT)),
    FlagRule("F 騎手の上積み", "人", "前の走の騎手より、前の年の勝率が 3ポイント以上高い騎手に替わった",
             lambda x: (x["jockey_rate"] - x["prev_jockey_rate"]) >= _JOCKEY_GAP),
    FlagRule("G 前で運べば走る馬が前走は後ろで負けた", "枠と展開",
             "逃げ・先行で3着以内が2回以上あり、差し・追込での3着以内より多いのに、前の走は差し・追込の位置で6着以下（いつもの形で走れなかった負け）",
             lambda x: (x["front_places_before"] >= 2) & (x["front_places_before"] > x["back_places_before"])
             & x["prev_style"].isin(["差し", "追込"]) & (x["prev_finish"] >= _BEATEN)),
)

#: どの型にも当てはまらない馬の名前。
NO_TYPE = "Z 手がかりなし"
