"""比べるための評価指標と、検証期間で線を決める部品（既存モデルの修正計画の 3）。

複勝的中の確率・見込みの倍率（``yosou.shared.place_value``）と、人気馬の危険の線（``yosou.favorites_out_of_top3.danger``）は、
予想の出力にも使うので、予想のパッケージにある。

| 名前 | 仕事 |
|---|---|
| ``BinaryScores`` | 二値の予想（3着以内・4着以下）の確率の誤差（ログ損失・Brier）と見分けやすさ（AUC・人気別 AUC） |
| ``PopularityBand`` | 単勝人気を帯（1・2・3・4〜5・6〜9・10〜）にする |
| ``BootstrapInterval`` | 回収率の推定幅（開催日を単位にしたブートストラップ） |
| ``ThresholdChooser`` | 期待値の線を、検証期間の回収率で決める |
| ``ConservativeRate`` | 回収率の控えめな見積もり（運が悪い方に転んだときの値。開催日を単位にしたばらつきから） |
"""

from .binary_scores import BinaryScores
from .bootstrap_interval import BootstrapInterval
from .conservative_rate import ConservativeRate
from .popularity_band import PopularityBand
from .threshold_chooser import ThresholdChooser

__all__ = ["BinaryScores", "PopularityBand", "BootstrapInterval", "ThresholdChooser", "ConservativeRate"]
