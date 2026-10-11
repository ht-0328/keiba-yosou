"""確かめられる材料の一覧（入口⑭ ``material_check.py --material`` で選ぶ）。"""

from __future__ import annotations

from yosou.ability_score import ABILITY_SCORE_FEATURES

from .ability_score_table_builder import AbilityScoreTableBuilder
from .material import Material

#: 材料の名前 → 材料。足すときは、予想のパッケージに材料の部品（特徴量の一覧・足す部品・外す部品）を作ってから、ここに1行足す。
MATERIALS: dict[str, Material] = {
    "能力スコア": Material(
        "ascore", "能力スコア", "T", ABILITY_SCORE_FEATURES, AbilityScoreTableBuilder,
        design="設計書「買うレースと買い目を決める」04（能力指数を今回の斤量で直し、レース内の偏差・2位との差・順位にする）",
    ),
}


def material_named(name: str) -> Material:
    """名前から引く。知らなければ ``ValueError``。"""
    if name not in MATERIALS:
        raise ValueError(f"知らない材料です: {name}（{' / '.join(MATERIALS)}）")
    return MATERIALS[name]
