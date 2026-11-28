"""今の1着の確率を、締め切り前に分かる材料で直す（研究「的中実績の公開ルール」の 02。公開ルールの ◎ と期待値に使う。印は変えない）。

今の1着の確率のロジットを出発点にして、券種どうしのずれ（単勝・複勝・馬連から見た率と、予想の確率の比）・人気と順位・頭数・
レースの中身と馬の事情（事実表の数の列）で上げ下げを学ぶ LightGBM（木を小さく縛り、種を変えた5本の平均）。

| クラス | 仕事 |
|---|---|
| ``QuinellaTop2`` | 馬連の板から、馬ごとの馬連から見た2着以内率を出す |
| ``WinCorrectionFeatures`` | 1頭1行の表から、出発点と材料の表を作る |
| ``WinCorrectionModel`` | 学ぶ・保存する・読む・直した確率を出す |
"""

from .quinella_top2 import QUINELLA_TOP2, QuinellaTop2
from .win_correction_features import FACT_COLUMNS, FEATURES, WinCorrectionFeatures
from .win_correction_model import WinCorrectionModel

__all__ = ["FACT_COLUMNS", "FEATURES", "QUINELLA_TOP2", "QuinellaTop2", "WinCorrectionFeatures", "WinCorrectionModel"]
