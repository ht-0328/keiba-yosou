"""危険な人気馬の「理由」（設計書「買うレースと買い目を決める」07 の 3）を、その馬の材料の値から並べる。"""

from __future__ import annotations

import pandas as pd

from yosou.ability_score import features as ability_score
from yosou.development_score import DEFAULT_LINE as PACE_LINE
from yosou.development_score import names as score_names
from yosou.shared.feature import POOL_SUPPORT_NAMES
from yosou.track_bias import DEFAULT_LINE as BIAS_LINE
from yosou.track_bias import names as bias_names
from yosou.weight_table import DEFAULT_LINE as WEIGHT_LINE
from yosou.weight_table import names as weight_names

#: 3連単から見た勝率と単勝の比（log）の列（まとまり N の最初）。負なら、3連単の人は単勝の人より低く見ている。
_TRIFECTA_RATIO = POOL_SUPPORT_NAMES[0]
#: 能力スコアの順位の列と、それが無いときの代わり（馬の力の材料の能力指数の順位）。レース内 3位以下なら「能力で見劣る」。
_ABILITY_RANK, _INDEX_RANK, ABILITY_RANK_LINE = ability_score.RANK, "指数_条件の重み_順位", 3


class DangerReasons:
    """判定の条件ではなく、人が読むための理由。その馬の特徴量の値（モデルに渡した材料。足していない材料は無いので出ない）から、
    当てはまるものを並べる。"""

    def of(self, features: pd.Series) -> list[str]:
        reasons = []
        ratio = _value(features, _TRIFECTA_RATIO)
        if ratio is not None and ratio < 0:
            reasons.append(f"券種どうしの食い違い（3連単から見た勝率が単勝から見た勝率より低い。比の log {ratio:+.2f}）")
        score = _value(features, score_names.SCORE)
        if score is not None and score <= -PACE_LINE:
            reasons.append(f"展開不利（展開スコア {score:+.3f} ≤ −{PACE_LINE:g}）")
        bias = _value(features, bias_names.CORRECTION)
        if bias is not None and bias <= -BIAS_LINE:
            reasons.append(f"バイアス逆（バイアスの補正 {bias:+.3f} ≤ −{BIAS_LINE:g}）")
        discount = _value(features, weight_names.DISCOUNT)
        if discount is not None and discount <= WEIGHT_LINE:
            reasons.append(f"体重の割引（馬体重の表 {discount:+.3f} ≤ {WEIGHT_LINE:g}）")
        rank = _value(features, _ABILITY_RANK)
        if rank is None:
            rank = _value(features, _INDEX_RANK)
        if rank is not None and rank >= ABILITY_RANK_LINE:
            reasons.append(f"能力で見劣る（能力スコアがレース内 {rank:.0f}位）")
        return reasons


def _value(features: pd.Series, name: str) -> float | None:
    value = features.get(name)
    if value is None or pd.isna(value):
        return None
    return float(value)
