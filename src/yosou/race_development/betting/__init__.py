"""印・買い目・当たる確率・精算・回収率のまとめ（設計書 04 の betting/・06 の図4・図5・16 の 7.・8.）。

年ごとの確かめ（``backtest``）と予測（``predict``）の両方で使う。モデルは使わず、確率と払戻の表だけを扱う。
参照するのは ``yosou.shared`` だけ（券種は ``yosou.shared.betting``、払戻・確定オッズの読み込みは ``yosou.shared.repository``）。

| クラス | 仕事 |
|---|---|
| ``Ticket`` | 1つの買い目（レース・券種・馬番の並び・買い方の名前・金額 100円）。``combo`` は払戻の組番と同じ形 |
| ``TicketProbability`` | 1レースの3連単の確率の表から、1つの券種の全部の買い目の当たる確率を出す（複勝は 7頭立て以下なら 2着以内） |
| ``Mark`` | 6つの印（◎○▲△☆注）を表す値 |
| ``MarkAssigner`` | 1着の確率・単勝オッズ・先頭の確率から、1レースの馬に印を付ける（図4） |
| ``PopularityMarkAssigner`` | 比べる基準。単勝オッズの低い順に ◎○▲△ を付ける |
| ``MarkTicketRule`` | 印から、券種ごとの印どおりの買い目を作る |
| ``ExpectedValueTicketRule`` | 券種ごとに、当たる確率 × 確定オッズ が線（既定 1.0）以上の買い目を全部作る |
| ``TicketSettler`` | 買い目を払戻と照らし合わせて、払戻と当たったかを付ける。不成立・特払の券種は見送り（図5） |
| ``ReturnSummary`` | 精算した買い目を、買い方 × 券種 × 年（と合計）ごとにまとめ、的中率・回収率を出す |

表の列の名前は ``column_names.py``。買い方の名前は ``MODEL_MARK_RULE``・``POPULARITY_MARK_RULE``（印どおり）と、
``ExpectedValueTicketRule`` の ``name``（既定「期待値 1.0 以上（モデル）」）。
"""

from . import column_names
from .expected_value_ticket_rule import ExpectedValueTicketRule
from .mark import Mark
from .mark_assigner import MarkAssigner
from .mark_ticket_rule import MODEL_MARK_RULE, POPULARITY_MARK_RULE, MarkTicketRule
from .popularity_mark_assigner import PopularityMarkAssigner
from .return_summary import TOTAL_YEAR, ReturnSummary
from .ticket import Ticket
from .ticket_probability import TicketProbability
from .ticket_settler import TicketSettler

__all__ = [
    "Ticket", "TicketProbability", "Mark", "MarkAssigner", "PopularityMarkAssigner", "MarkTicketRule",
    "ExpectedValueTicketRule", "TicketSettler", "ReturnSummary",
    "MODEL_MARK_RULE", "POPULARITY_MARK_RULE", "TOTAL_YEAR", "column_names",
]
