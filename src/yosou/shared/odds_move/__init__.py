"""オッズの動き（前日の最後の単勝オッズ → 今の単勝オッズ）で、当日の予想の確率を直す（設計書「近走と適性から3着以内を予想」の 15 の 22）。

前日から当日にかけて売れた馬（オッズが下がった馬）は、今のオッズから見た以上に来やすく、売れなかった馬は来にくい。
今の予想の確率のロジットを出発点にして、オッズの動きの材料（``OddsMoveFeatures``）を足すロジスティック回帰で直す。

| クラス | 仕事 |
|---|---|
| ``OddsMoveFeatures`` | 単勝オッズと前日の最後の単勝オッズから、直しの材料（オッズの動き・動き × log(オッズ)・前日のオッズがあるか）を作る |
| ``OddsMoveWeights`` | 1つの目的（3着以内か1着）の直しの重み（切片と材料ごとの重み） |
| ``OddsMoveFitter`` | 今の予想の確率と結果から、直しの重みを学ぶ（重みに弱い罰） |
| ``OddsMoveCorrection`` | 重みで確率を直す（1着はレースの中で合計 1 にそろえる） |
"""

from .odds_move_correction import TARGET_TOP3, TARGET_WIN, OddsMoveCorrection
from .odds_move_features import OddsMoveFeatures
from .odds_move_fitter import OddsMoveFitter
from .odds_move_weights import OddsMoveWeights

__all__ = ["OddsMoveCorrection", "OddsMoveFeatures", "OddsMoveFitter", "OddsMoveWeights", "TARGET_TOP3", "TARGET_WIN"]
