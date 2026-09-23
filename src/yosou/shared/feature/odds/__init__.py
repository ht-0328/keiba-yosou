"""単勝オッズから見た確率（既存モデルの修正計画の 2「オッズの使い方」）。

単勝オッズは「馬券を買う人たち全体が、どの馬がどれだけ勝ちそうと見ているか」を表す。ここでは単勝オッズから、
勝率・2着以内率・3着以内率を出す。予想モデルは、このうち3着以内率（4着以下を当てる予想はその裏返し）を
出発点（基準）にして、近走や適性で上げ下げした分だけを学ぶ。

「1 ÷ 単勝オッズ」をそろえた勝率を、そのまま3着以内の確率にはしない。勝率 0.3 の馬が3着以内に入る確率は
0.3 ではなく、ほかの馬が1着・2着になったあとに残る分も足した値になる。その足し方に Harville の式を使う。

| クラス | 仕事 |
|---|---|
| ``MarketWinProbability`` | 単勝オッズの逆数を、レース内で合計 1 にそろえた勝率（オッズから見た勝率） |
| ``HarvillePlaces`` | 勝率から、1着・2着以内・3着以内に入る確率を出す（Harville の式） |
| ``MarketPlaces`` | 出走の行から、上の2つを続けて呼び、オッズから見た勝率・2着以内率・3着以内率を出す |

列の名前（``WIN_RATE``・``TOP2_RATE``・``TOP3_RATE``）は ``column_names.py``。
"""

from .column_names import TOP2_RATE, TOP3_RATE, WIN_RATE
from .harville_places import HarvillePlaces
from .market_places import MarketPlaces
from .market_win_probability import MarketWinProbability

__all__ = ["MarketWinProbability", "HarvillePlaces", "MarketPlaces", "WIN_RATE", "TOP2_RATE", "TOP3_RATE"]
