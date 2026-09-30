"""穴馬の「買い」の判定（設計書 16 の 3）。

3着以内に入る確率の高さで買うと、もともと来やすい人気上位の穴馬ばかりになる。ここでは複勝の期待値（複勝的中の確率 ×
見込みの払戻の倍率）に線を引き、線以上の穴馬を「買い」とする。線は時点（前日・当日）× 区分（中穴・大穴）ごとに、
学習のときに検証期間で決めて、モデルと一緒に保存する（``BuyLineRepository``）。

| クラス | 仕事 |
|---|---|
| ``BuyLineChooser`` | 線の候補ごとの検証期間の成績を出し、決まりに合う線を選ぶ |
| ``BuyJudge`` | 予測の結果に、その馬の区分の線と「買い」の印を足す |
| ``DayBootstrapInterval`` | 回収率の推定幅（開催日を単位にしたブートストラップ）。確かめる期間の成績に添える |
"""

from .buy_judge import BUY_LINE, IS_BUY, BuyJudge
from .buy_line_chooser import CANDIDATES, HIT_RATE, LINE, MIN_POINTS, PAYBACK, POINTS, BuyLineChooser
from .day_bootstrap_interval import DayBootstrapInterval

__all__ = [
    "BuyLineChooser", "BuyJudge", "DayBootstrapInterval",
    "CANDIDATES", "MIN_POINTS", "LINE", "POINTS", "HIT_RATE", "PAYBACK", "BUY_LINE", "IS_BUY",
]
