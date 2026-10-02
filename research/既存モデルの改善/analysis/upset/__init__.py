"""荒れ具合を、馬ごとの着順の確率から計算する新しい出し方（既存モデルの修正計画の 1「レースの荒れ具合」）。

現行の荒れ具合の予想は、レース単位の特徴量から4段階を直接学ぶ。新しい出し方は、1頭ごとの勝率（オッズと3つの予想を
組み合わせたもの）から、券種ごとの組み合わせが当たる確率を出し、その組み合わせの確定オッズ（＝払戻）が
どの段階に入るかで確率を足し上げる。例: 3連単で 12万円の組み合わせが当たる確率が 0.004 なら、その 0.004 は
「大荒れ」（10万〜50万円）に入る。段階の線引きは現行と同じ（``UpsetLevelRule``）。

| 名前 | 仕事 |
|---|---|
| ``UpsetClassCalculator`` | 1レースの勝率と組み合わせのオッズから、券種ごとの4段階の確率を出す |
| ``UpsetCalculationRunner`` | 1つの区切りで、検証期間で勝率の出し方を決め、テスト期間の全レースの4段階の確率を出す |
| ``UpsetScores`` | 4段階の確率と正解から、正解率・ログ損失・マクロ F1・「中荒れ以上」の AUC を出す |
"""

from .upset_calculation_runner import UpsetCalculationRunner
from .upset_class_calculator import UpsetClassCalculator
from .upset_scores import UpsetScores

__all__ = ["UpsetClassCalculator", "UpsetCalculationRunner", "UpsetScores"]
