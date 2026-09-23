"""1レースの中で、各馬の勝率と、着順の組み合わせの確率を出す。

馬ごとの予想（3着以内・4着以下）は1頭ずつ独立に確率を出すので、そのままでは「1着と2着の組み合わせ」のような
券種の確率にならない。ここでは、単勝オッズから見た勝率に、予想モデルが出した上げ下げを足してレース内で勝率に直し
（``RaceStrengthModel``）、そこから着順の組み合わせの確率を出す（``FinishOrderProbability``）。

| 名前 | 仕事 |
|---|---|
| ``RaceStrengthModel`` | レースの中で「どの馬が勝つか」を学ぶ条件付きロジット。材料の重みを、勝った馬から決める |
| ``FinishOrderProbability`` | 勝率から、1着・2着・3着の並びの確率を出す（Stern の補正つき Harville の式） |
| ``SternExponentFitter`` | Stern の補正の強さ（2着・3着での人気馬の寄り方）を、実際の着順から決める |
| ``RaceFinishes`` | レースごとの（勝率, 1着・2着・3着の馬の位置）の並びを作る |
"""

from .finish_order_probability import FinishOrderProbability
from .race_finishes import RaceFinishes
from .race_strength_model import RaceStrengthModel
from .stern_exponent_fitter import SternExponentFitter

__all__ = ["RaceStrengthModel", "FinishOrderProbability", "SternExponentFitter", "RaceFinishes"]
