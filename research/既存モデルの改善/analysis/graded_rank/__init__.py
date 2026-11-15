"""順位で学ぶ予想（3案目。同じレースの馬の着順の並びを lambdarank で学び、1着と3着以内の確率にする）の部品。

| 名前 | 仕事 |
|---|---|
| ``RankModel`` | レースを組にして着順の並びを学ぶ（出発点はオッズから見た勝率の対数） |
| ``PlackettLuce`` | 点数を1着の確率（レースで合計 1）と3着以内の確率（Harville の式）にする。効き具合は検証の期間で合わせる |
| ``RankWindowTrainer`` | 1つの区切りで学び、テストの期間の確率を出す |
"""

from .plackett_luce import PlackettLuce
from .rank_model import RankModel
from .rank_window_trainer import RankWindowTrainer

__all__ = ["PlackettLuce", "RankModel", "RankWindowTrainer"]
