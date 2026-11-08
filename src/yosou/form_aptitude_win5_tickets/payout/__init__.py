"""配当の見積もり（設計書 09 の 2.、10 の 2.、06 の図2）。

| クラス | 仕事 |
|---|---|
| ``PoolSizeEstimate`` | その日の発売票数を、それより前の同じ曜日の種類の直近 10回の中央値で見積もる |
| ``PayoutPool`` | その日の払戻に回るお金の見込みを表す値（発売票数の見積もりとキャリーオーバー） |
| ``ComboMarketProbability`` | 過去の当たり組の5頭の確定単勝オッズから、市場の組の確率を出す |
| ``PayoutFeatures`` | 組の材料（市場の組の確率の逆数の対数、キャリーオーバーの比の対数）を作る |
| ``PayoutEstimator`` | 配当の見積もりの式（傾き・切片・戻すときの補正）。過去の当たり組で作り、組の材料から式の値を出す |
| ``PayoutCeiling`` | 式の値に、自分の1票と払戻の上限を当てて、見積もりの配当にする |
| ``PayoutTrainingRows`` | 過去の WIN5 の表から、式を作るのに使う当たり組の行（材料と払戻）を作る |

``win5_rules.py`` は WIN5 のルールの値（1点 100円・払戻率 70%・払戻の上限）。
過去の WIN5 の表の列の名前は ``repository/win5_columns.py`` を参照する（読むのはリポジトリ）。
"""

from .combo_market_probability import ComboMarketProbability
from .payout_ceiling import PayoutCeiling
from .payout_estimator import PayoutEstimator
from .payout_features import CARRY_LOG, FEATURE_COLUMNS, INVERSE_LOG, PayoutFeatures
from .payout_pool import PayoutPool
from .payout_training_rows import POOL_ESTIMATE, PayoutTrainingRows
from .pool_size_estimate import PoolSizeEstimate
from .win5_rules import PAYOUT_CEILING, PAYOUT_RATE, TICKET_YEN

__all__ = [
    "PoolSizeEstimate", "PayoutPool", "ComboMarketProbability", "PayoutFeatures", "PayoutEstimator", "PayoutCeiling",
    "PayoutTrainingRows", "FEATURE_COLUMNS", "INVERSE_LOG", "CARRY_LOG", "POOL_ESTIMATE", "TICKET_YEN", "PAYOUT_RATE",
    "PAYOUT_CEILING",
]
