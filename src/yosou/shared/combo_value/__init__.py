"""組み合わせの券種（3連複・3連単など）の買い目の期待値（設計書「買うレースと買い目を決める」07 の 2）。

買い目（組）の確率を、1着の確率から Harville の式で組み立てると、市場が持つ「この馬どうしは一緒に来やすい」といった組ごとの情報を
捨ててしまい、人気薄の組を見積もりすぎる（研究「回収率100超」の 05）。ここでは **市場が見た組の確率を出発点にして、組の各位置の馬の
「モデル ÷ 市場」の比だけを掛ける**。

| クラス | 仕事 |
|---|---|
| ``HorseRatio`` | 馬ごとの「モデル ÷ 市場」の比（1着の比と3着以内の比）を出す |
| ``ComboExpectedValue`` | 組の期待値 = 券種の払戻率 × 組の各位置の馬の比の積。組の確率 = 期待値 ÷ オッズ |
| ``HorseStrength`` | 馬ごとの、レースで合計 1 にそろえた1着の確率と「モデル ÷ 市場」の比（下の組の確率のもと） |
| ``TrifectaSources`` | 3連単の全部の組に、市場の確率とモデルの Harville の確率を付ける |
| ``PoolFolding`` | 3連単の組の確率を足し合わせて、馬単・馬連・ワイド・3連複の組の確率にする |
| ``ComboBlendFeatures`` | 1つの券種の全部の組に、4つのもと（その券種自身の市場・3連単から見た市場・モデルの Harville・モデルの比）の対数を付ける |
| ``ComboBlendWeights`` | 4つのもとの重み（1つの券種ぶん） |
| ``BracketBlendWeights`` | 枠連の組の確率の4つのもと（枠連の市場・馬連の市場・3連単から見た市場・モデルの Harville）の重み |
| ``ComboBlend`` | 重みを掛けて組の確率（レースで合計 1）と期待値（確率 × オッズ）を出す |
| ``ComboBlendFitter`` | 重みを、当たった組に合わせて推定する（条件付きロジット） |

市場が見た組の確率は「払戻率 ÷ オッズ」なので、期待値（確率 × オッズ）からはオッズが消え、払戻率と比の積だけで決まる。
つまり「期待値の高い組」とは「モデルが市場より高く見た馬をそろえた組」で、オッズの高い組ほど期待値が高く出ることは無い。

ただし、この式は人気薄の組の確率を大きく見積もりすぎる（期待値の帯を上げても回収率が上がらない）。**実際に買う馬連・馬単は、
4つのもとに重みを掛けて合わせた組の確率（``ComboBlend``）で期待値を出す**（研究「複勝以外の回収率100超」の docs/04）。
重みは市場とモデルのどちらをどれだけ信じるかで、当たった組に合わせて推定する。
"""

from .bracket_blend_weights import BracketBlendWeights
from .combo_blend import ComboBlend
from .combo_blend_features import FEATURE_COLUMNS, ComboBlendFeatures
from .combo_blend_fitter import HIT, ComboBlendFitter
from .combo_blend_weights import ComboBlendWeights
from .combo_columns import horse_columns, join_combo, split_combo
from .combo_expected_value import ComboExpectedValue
from .horse_ratio import TOP3_RATIO, WIN_RATIO, HorseRatio
from .horse_strength import HorseStrength
from .pool_folding import PoolFolding
from .trifecta_sources import HARVILLE, MARKET, TrifectaSources

__all__ = ["BracketBlendWeights", "ComboExpectedValue", "HorseRatio", "WIN_RATIO", "TOP3_RATIO", "HorseStrength", "TrifectaSources", "MARKET", "HARVILLE",
           "PoolFolding", "ComboBlendFeatures", "FEATURE_COLUMNS", "ComboBlendWeights", "ComboBlend", "ComboBlendFitter", "HIT",
           "horse_columns", "split_combo", "join_combo"]
