"""この予想の、学習データの評価用の列の名前（設計書 08 の 2）。

目的変数の列の名前（荒れ具合（単勝）など）は ``BetType.column_name``、レースの結果の列（勝ち馬の人気 など）は
共通の ``yosou.shared.dataset`` にある。ここには、払戻の列の名前を置く。
"""

from __future__ import annotations

from yosou.shared.repository.race_payout_repository import POPULARITY, YEN

from .bet_type import BetType


def payout_column(bet: BetType) -> str:
    """その券種の払戻（100円あたりの円）の列の名前。"""
    return f"{bet.label}の払戻"


def payout_popularity_column(bet: BetType) -> str:
    """その券種の払戻の人気順（当たった組み合わせが何番人気だったか）の列の名前。"""
    return f"{bet.label}の払戻の人気順"


#: 評価用の列に残す払戻の列（学習データの列名 → 共通の ``RacePayoutRepository`` の列名）。
PAYOUT_COLUMNS: dict[str, str] = {
    **{payout_column(bet): f"{bet.key}_{YEN}" for bet in BetType},
    **{payout_popularity_column(bet): f"{bet.key}_{POPULARITY}" for bet in BetType},
}
