"""券種ごとの決まり（元DB のどの表を読み、買い目をどう番号にし、何点まで買うか）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: 1レースの馬番の上限。JRA は最大 18頭立て。買い目の番号はこの数を底にして作る。
MAX_HORSES = 18
#: 1つのオッズ列を持つ券種の、値段の式（元DB のオッズは 10倍の整数）。
_SINGLE_ODDS = "try_cast(オッズ as double) / 10.0"
#: ワイドは幅（最低〜最高）でしか出ないので、最低オッズを読む。受け取る額は別に見積もる。
_LOWEST_ODDS = "try_cast(最低オッズ as double) / 10.0"


@dataclass(frozen=True)
class TicketKind:
    """1つの券種の決まり。

    - ``key``: 中間データのファイル名に使う短い名前。
    - ``name``: 表に出す名前。
    - ``horses``: 買い目に入る馬の数（単勝 1、馬連・ワイド・馬単 2、3連複・3連単 3）。
    - ``ordered``: 着順どおりに当てる券種か（単勝・馬単・3連単）。
    - ``odds_table`` ・ ``odds_combo`` ・ ``odds_price``: 元DB のオッズの表・組の列・値段の式。
    - ``payout_table`` ・ ``payout_combo``: 元DB の払戻の表・組の列。
    - ``lowest_price``: 値段が最低オッズか（ワイド）。受け取る額を帯ごとの倍率で見積もる。
    - ``cap``: 1レースで買う点数の上限（期待値の高い順に残す）。
    - ``bands``: 確率を直すときの、オッズの帯の区切り。
    """

    key: str
    name: str
    horses: int
    ordered: bool
    odds_table: str
    odds_combo: str
    odds_price: str
    payout_table: str
    payout_combo: str
    lowest_price: bool
    cap: int
    bands: tuple[float, ...]

    def horse_columns_sql(self, combo_column: str) -> str:
        """組の列（2桁ずつの馬番）を、馬番の列 h1〜h3 に分ける SQL の式。"""
        return ", ".join(
            f"try_cast(substr({combo_column}, {index * 2 + 1}, 2) as utinyint) as h{index + 1}"
            for index in range(self.horses))

    def flat_index(self, horse_numbers: np.ndarray) -> np.ndarray:
        """買い目（行 = 1点、列 = 組の馬番）を、確率の表の番号にする。

        例: 3連単の 3-1-5 は (3−1)×18² + (1−1)×18 + (5−1) = 652。
        """
        numbers = np.asarray(horse_numbers, dtype=np.int64).reshape(-1, self.horses) - 1
        weights = MAX_HORSES ** np.arange(self.horses - 1, -1, -1, dtype=np.int64)
        return numbers @ weights


#: 検証する券種。点数の上限は、研究「既存モデルの改善」の組み合わせた買い方と同じ。
TICKET_KINDS: tuple[TicketKind, ...] = (
    TicketKind("win", "単勝", 1, True, "o1__単勝オッズ", "馬番", _SINGLE_ODDS,
               "hr__単勝払戻", "馬番", False, 2, (0, 2, 5, 10, 20, 50, 100, 1e9)),
    TicketKind("wide", "ワイド", 2, False, "o3__ワイドオッズ", "組番", _LOWEST_ODDS,
               "hr__ワイド払戻", "組番", True, 5, (0, 2, 5, 10, 20, 50, 100, 1e9)),
    TicketKind("quinella", "馬連", 2, False, "o2__馬連オッズ", "組番", _SINGLE_ODDS,
               "hr__馬連払戻", "組番", False, 5, (0, 5, 10, 20, 50, 100, 300, 1e9)),
    TicketKind("exacta", "馬単", 2, True, "o4__馬単オッズ", "組番", _SINGLE_ODDS,
               "hr__馬単払戻", "組番", False, 5, (0, 5, 10, 20, 50, 100, 300, 1e9)),
    TicketKind("trio", "3連複", 3, False, "o5__3連複オッズ", "組番", _SINGLE_ODDS,
               "hr__3連複払戻", "組番", False, 10, (0, 10, 30, 100, 300, 1000, 1e9)),
    TicketKind("trifecta", "3連単", 3, True, "o6__3連単オッズ", "組番", _SINGLE_ODDS,
               "hr__3連単払戻", "組番", False, 30, (0, 30, 100, 300, 1000, 3000, 10000, 1e9)),
)
#: 短い名前 → 券種。
KINDS_BY_KEY: dict[str, TicketKind] = {kind.key: kind for kind in TICKET_KINDS}
