"""組の表（1行 = 1レース × 1券種 × 1つの組）を作る。

馬ごとの表と5券種の板から、市場の表 → 馬ごとの材料・レースごとの表 → 券種ごとの組の表（材料・出発点）の順に作り、
学習用には払戻（当たったか）を付け、外れを間引いて、共有のモデルのクラスが受け取る形に詰め替える。

| 名前 | 仕事 |
|---|---|
| ``PayoutBand`` | 1つの券種の帯（学ぶ下限・高配当の線・上限） |
| ``DEFAULT_BANDS``・``DEFAULT_VALUE_LINE`` | 5券種の既定の帯と、期待値の線の既定（1.05） |
| ``ComboTableBuilder`` | 入口。馬ごとの表と5券種の板から、券種ごとの組の表を作る（学習用の表づくりと本番の予測で同じもの） |
| ``MarketTableBuilder`` | 5券種の板から、券種ごとの市場の表（市場の確率 q・t）を作る（共有の ``combo_value`` の部品を呼ぶ） |
| ``TrifectaPoolWin`` | 3連単の板から見た、馬ごとの勝率 |
| ``HorseMaterials`` | 馬ごとの表から、馬ごとの材料（22個）を作る |
| ``RaceMaterials`` | 馬ごとの材料から、レースごとの表を作る |
| ``ComboMemberLookup`` | 組の各位置の馬の材料を、馬ごとの材料の表から引く |
| ``TicketTableAssembler`` | 1つの券種の対象の行を選び、材料のまとまりを順に付けて組の表にする |
| ``FinalMarketLoader`` | 期間ぶんの確定オッズの板（5券種）と払戻を、元DB から読む。戻り値は ``FinalMarket`` |
| ``HitLabeler`` | 組の表に、開催日と、当たったか・払戻を付ける |
| ``MissSampling`` | 学習の行を選ぶ（当たりは全部、外れは間引いて重みを付ける）。割合は ``MISS_KEEP_RATES`` |
| ``ModelDataFactory`` | 組の表を ``TrainingData``・``PredictionData`` に詰め替える |

列の名前は ``column_names.py``、表の列の並びは ``table_columns.py``。
"""

from .combo_member_lookup import ComboMemberLookup
from .combo_table_builder import ComboTableBuilder
from .default_bands import DEFAULT_BANDS, DEFAULT_VALUE_LINE
from .final_market import FinalMarket
from .final_market_loader import FinalMarketLoader
from .hit_labeler import HitLabeler
from .horse_materials import MARK_NUMBERS, HorseMaterials
from .market_table_builder import MarketTableBuilder
from .miss_keep_rates import MISS_KEEP_RATES
from .miss_sampling import MissSampling
from .model_data_factory import ModelDataFactory
from .payout_band import PayoutBand
from .race_materials import RaceMaterials
from .ticket_table_assembler import TicketTableAssembler
from .trifecta_pool_win import TrifectaPoolWin

__all__ = [
    "PayoutBand", "DEFAULT_BANDS", "DEFAULT_VALUE_LINE", "ComboTableBuilder", "MarketTableBuilder", "TrifectaPoolWin",
    "HorseMaterials", "MARK_NUMBERS", "RaceMaterials", "ComboMemberLookup", "TicketTableAssembler", "FinalMarket", "FinalMarketLoader",
    "HitLabeler", "MissSampling", "MISS_KEEP_RATES", "ModelDataFactory",
]
