"""能力スコア: 能力指数を今回の斤量で直し、レースの中での位置（偏差・2位との差・順位）にする（設計書「買うレースと買い目を決める」04）。

能力指数（近8走のスピード指数を、新しさと今回の条件への近さで重み付けした平均）は、馬の力の材料（M）の「指数_条件の重み」として
全頭の予想にもう入っている。この部品は、それを今回の斤量の分だけ直し（スピード指数は 55kg にそろえてあるので、1kg あたり 0.5点を引く）、
同じレースの相手と比べた位置に直す。全頭の予想の特徴量（まとまり T。4個）として足す。

| 名前 | 仕事 |
|---|---|
| ``AbilityScoreColumns`` | 能力指数と今回の斤量から、能力スコア・偏差・2位との差・順位の4列を作る |
| ``AbilityScoreAttachment`` | 学習データ・予測用データに T の4列を足す（S の ``ScoreAttachment`` と同じ形。外の表は要らない） |
| ``AbilityScoreFreeData`` | 学習データ・予測用データから T を外す（採用しなかったモデルに渡す前に） |
| ``RaceAbilityScoreAttacher`` | 1レースの予測用データに T を足す関数の形（全頭の予想の予測の流れに渡す） |
| ``ABILITY_SCORE_FEATURES`` | 能力スコアを予想の特徴量にするときの一覧（まとまり T。4個） |
"""

from .ability_score_attachment import AbilityScoreAttachment
from .ability_score_columns import ABILITY_INDEX, BASE_CARRIED_KG, CARRIED, POINTS_PER_KG, AbilityScoreColumns
from .ability_score_free_data import AbilityScoreFreeData
from .features import ABILITY_SCORE_FEATURES, ABILITY_SCORE_NAMES
from .race_ability_score_attacher import RaceAbilityScoreAttacher

__all__ = [
    "AbilityScoreColumns", "AbilityScoreAttachment", "AbilityScoreFreeData", "RaceAbilityScoreAttacher",
    "ABILITY_SCORE_FEATURES", "ABILITY_SCORE_NAMES", "ABILITY_INDEX", "CARRIED", "POINTS_PER_KG", "BASE_CARRIED_KG",
]
