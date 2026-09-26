"""印・買い目・精算の表の列の名前（設計書 04 の betting/・16 の 7.・8.）。

払戻・確定オッズの表の列（``combo``・``yen``・``odds``）は、共通のリポジトリの名前と同じにして、そのまま突き合わせる。
"""

from __future__ import annotations

from yosou.shared.repository.final_odds_repository import ODDS
from yosou.shared.repository.payout_repository import COMBO, YEN

__all__ = [
    "RACE_ID", "HORSE_NO", "WIN_PROBABILITY", "WIN_ODDS", "LEADER_PROBABILITY", "MARK", "FIRST", "SECOND", "THIRD",
    "PROBABILITY", "COMBO", "YEN", "ODDS", "TICKET_TYPE", "STAKE", "RULE", "EXPECTED_VALUE", "PAYOUT", "HIT", "YEAR",
    "STAKE_YEN", "NO_MARK",
]

#: レースの鍵（共通のリポジトリと同じ ``race_id``）。
RACE_ID = "race_id"

#: 印を付ける1レースの表（1行 = 1頭）の列。単勝オッズは、無い時点（木曜）なら欠損値。
HORSE_NO = "horse_no"
WIN_PROBABILITY = "win_probability"
WIN_ODDS = "win_odds"
LEADER_PROBABILITY = "leader_probability"
#: 付けた印（``Mark`` の値の文字列。印の無い馬は ``NO_MARK``）。
MARK = "mark"
NO_MARK = ""

#: 1レースの3連単の確率の表の列（1着・2着・3着の馬番と、その並びの確率）。
FIRST, SECOND, THIRD = "first", "second", "third"
#: 当たる確率（3連単の表の ``probability`` も、券種ごとの買い目の確率も同じ名前）。
PROBABILITY = "probability"

#: 買い目の表（1行 = 1点）の列。``ticket_type`` は ``TicketType.key``（``trio`` など）、``stake`` は円。
TICKET_TYPE = "ticket_type"
STAKE = "stake"
RULE = "rule"
#: 期待値で買うときに足す列（当たる確率 × 確定オッズ）。
EXPECTED_VALUE = "expected_value"

#: 精算で足す列。``payout`` は戻る円（外れは 0）、``hit`` は当たったか。
PAYOUT = "payout"
HIT = "hit"
#: 回収率をまとめる前に、精算した買い目に足す列（開催年）。
YEAR = "year"

#: 1点の金額（円）。
STAKE_YEN = 100
