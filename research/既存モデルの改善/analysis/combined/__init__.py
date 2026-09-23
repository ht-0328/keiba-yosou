"""直した予想（全頭・穴馬・人気馬）を組み合わせて、1レースの中の勝率を出す。

1. ``HorseTableBuilder``: 区切りごとに、全頭の学習データの表（ID・評価用の列・目的変数・基準）に、3つの予想の予測
   （検証とテスト）を並べた、1行 = 1頭の表を作る。
2. ``StrengthFeatures``: その表から、レースの中の勝率を学ぶ材料（オッズから見た勝率の log と、3つの予想の上げ下げ）を作る。
   予想の「上げ下げ」は、予想の確率のロジットから、オッズから作った基準のロジットを引いた値（3着以内の向き）。
3. ``RaceProbabilityBuilder``: 検証期間で、材料の重み（``RaceStrengthModel``）と Stern の補正（``SternExponentFitter``）を
   決め、テスト期間の勝率を出す。テスト期間の結果は、どちらを決めるのにも使わない。

列の名前は ``horse_columns.py``。
"""

from . import horse_columns
from .horse_table_builder import HorseTableBuilder
from .race_probability_builder import RaceProbabilityBuilder, RaceProbabilityFit
from .strength_features import StrengthFeatures

__all__ = ["HorseTableBuilder", "StrengthFeatures", "RaceProbabilityBuilder", "RaceProbabilityFit", "horse_columns"]
