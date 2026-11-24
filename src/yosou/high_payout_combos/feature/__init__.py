"""材料（特徴量）を作る。材料のまとまりごとに1クラス。

入力は、市場の表（1行 = 1券種の1組。``dataset`` の ``MarketTableBuilder``）と、組の馬ごとの材料（``ComboMembers``）と、
レースごとの表（``dataset`` の ``RaceMaterials``）。どのクラスも、行の並びを変えずに材料の列だけを返す。

| 名前 | 仕事 |
|---|---|
| ``OwnMarketFeatures`` | A. その券種の市場（オッズ・市場の確率 q・3連単から見た確率 t・その差） |
| ``CrossMarketFeatures`` | B. ほかの券種の市場（組に含まれる2頭・3頭の組の、ほかの券種での市場の確率） |
| ``HarvilleFeatures`` | C. Harville の式で出した組の確率（予想の1着の確率からと、単勝オッズから見た勝率から） |
| ``HarvilleProbability`` | Harville の式そのもの（着順どおり・並びを問わない・2頭とも3着以内） |
| ``WidePairProbability`` | ワイドの組の Harville の確率（レースごとに全部の2頭の組を作って引く） |
| ``PositionHorseFeatures`` | D. 組の位置ごとの馬の材料（20個 × 組の馬の数） |
| ``ComboSummaryFeatures`` | E. 組の馬の材料の和・最小・最大・数 |
| ``RaceFeatures`` | F. レースの材料（頭数・1番人気の値・危険な1番人気を外した組か など） |
| ``RegionFeatures`` | F. そのレースの「学ぶ帯」の大きさ（組の数・市場の確率の合計・Harville の確率の合計） |
| ``ComboMembers`` | 組の馬ごとの材料（行 × 組の位置 × 材料）と、材料にするときの馬の並び |
| ``CATALOGS``・``feature_catalog()`` | 券種ごとの材料の一覧（``FeatureCatalog``） |
| ``TICKET_TYPES`` | 扱う5つの券種 |

列の名前は ``column_names.py``、馬ごとの材料の名前は ``material_names.py``、穴馬の決まりは ``longshot_rule.py``。
材料の定義は、パッケージの docstring（``yosou.high_payout_combos``）と各クラスの docstring に書く。
"""

from .combo_members import ComboMembers
from .combo_summary_features import ComboSummaryFeatures
from .cross_market_features import REQUIRED_MARKETS, CrossMarketFeatures
from .feature_catalog import CATALOGS, TICKET_TYPES, feature_catalog
from .harville_features import LOG_HV, HarvilleFeatures
from .harville_probability import HarvilleProbability
from .own_market_features import OwnMarketFeatures
from .position_horse_features import PositionHorseFeatures
from .race_features import RACE_MATERIALS, RaceFeatures
from .region_features import RegionFeatures
from .wide_pair_probability import WidePairProbability

__all__ = [
    "OwnMarketFeatures", "CrossMarketFeatures", "REQUIRED_MARKETS", "HarvilleFeatures", "LOG_HV", "HarvilleProbability",
    "WidePairProbability", "PositionHorseFeatures", "ComboSummaryFeatures", "RaceFeatures", "RACE_MATERIALS", "RegionFeatures",
    "ComboMembers", "CATALOGS", "feature_catalog", "TICKET_TYPES",
]
