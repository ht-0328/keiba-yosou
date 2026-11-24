"""組の表（1行 = 1レース × 1券種 × 1つの組）の、材料ではない列の名前。"""

from ..feature.column_names import COMBO, HORSE_NO, ODDS, RACE_ID

#: 開催日と、券種の名前（``TicketType`` の label。例 ``馬連``）。
RACE_DATE = "race_date"
TICKET_TYPE = "ticket_type"
#: 出発点（市場の確率 q のロジット）。モデルはここからの上げ下げだけを学ぶ。
BASELINE = "baseline"
#: 目的変数（その組が当たったら 1）と、評価用の 100円あたりの払戻（外れは 0）。
HIT = "hit"
PAYOUT = "payout"
#: 学習の行の重み（間引いた外れは 1 ÷ 残す割合、当たりは 1）。
WEIGHT = "weight"
#: 予測の列。その組が当たる確率（2つのモデルの平均）、期待値（確率 × オッズ）、その券種の市場の確率 q。
PROBABILITY = "probability"
VALUE = "value"
MARKET_PROBABILITY = "market_probability"
#: 組の馬番の並び（整数のタプル。例 ``(3, 7)``）。1レースの予測の結果に付ける。
HORSES = "horses"

__all__ = [
    "RACE_ID", "RACE_DATE", "HORSE_NO", "TICKET_TYPE", "COMBO", "ODDS", "BASELINE", "HIT", "PAYOUT", "WEIGHT",
    "PROBABILITY", "VALUE", "MARKET_PROBABILITY", "HORSES",
]
