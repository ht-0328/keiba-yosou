"""確かめられる材料の一覧（入口⑭ ``material_check.py --material`` で選ぶ）。"""

from __future__ import annotations

from yosou.ability_score import ABILITY_SCORE_FEATURES
from yosou.shared.feature import PredictionTiming
from yosou.track_bias import TRACK_BIAS_FEATURES
from yosou.weight_table import WEIGHT_DISCOUNT_FEATURES

from .ability_score_table_builder import AbilityScoreTableBuilder
from .material import Material
from .track_bias_table_builder import TrackBiasTableBuilder
from .weight_discount_table_builder import WeightDiscountTableBuilder

#: 材料の名前 → 材料。足すときは、予想のパッケージに材料の部品（特徴量の一覧・足す部品・外す部品）を作ってから、ここに1行足す。
MATERIALS: dict[str, Material] = {
    "能力スコア": Material(
        "ascore", "能力スコア", "T", ABILITY_SCORE_FEATURES, AbilityScoreTableBuilder,
        design="設計書「買うレースと買い目を決める」04（能力指数を今回の斤量で直し、レース内の偏差・2位との差・順位にする）",
    ),
    "トラックバイアス": Material(
        "tbias", "トラックバイアス", "U", TRACK_BIAS_FEATURES, TrackBiasTableBuilder,
        timings=(PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY),
        design="設計書「買うレースと買い目を決める」06 の 1（先に終わったレースで「市場の見立てより来た馬が内か外か・前か後ろか」を数え、"
               "過去の傾きと混ぜて、馬番の位置と展開の予想④の位置で馬ごとの補正にする。前日は前の日のレースだけ、当日はその日の先のレースも）",
    ),
    "馬体重の表": Material(
        "wdisc", "馬体重の表", "V", WEIGHT_DISCOUNT_FEATURES, WeightDiscountTableBuilder,
        timings=(PredictionTiming.RACE_DAY,),
        design="設計書「買うレースと買い目を決める」06 の 2（増減の帯 × 前走からの間隔 × 馬齢ごとの「実際の3着以内率 − 市場から見た3着以内率」を、"
               "馬ごとの体重の割引にする。馬体重の発表は当日なので当日だけ）",
    ),
}


def material_named(name: str) -> Material:
    """名前から引く。知らなければ ``ValueError``。"""
    if name not in MATERIALS:
        raise ValueError(f"知らない材料です: {name}（{' / '.join(MATERIALS)}）")
    return MATERIALS[name]
